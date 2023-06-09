from datetime import datetime, timedelta
from itertools import filterfalse
import logging
from pathlib import Path
import queue
import signal
import subprocess
import threading
import time
from typing import Optional

from picamera2.outputs import Output, FileOutput

import pandas as pd
import prctl

from capture_v2 import util
from capture_v2.log import logger


class CameraOutputSegmenter(Output):
    def __init__(
        self,
        clip_duration: int = 10,  # in seconds
        frame_rate: int = 10,
        gop_size: int = 10,  # sets key frame frequency
        pts=None,
        staging_dir="./staging",
        output_dir="./output",
    ):
        super().__init__(pts=pts)
        self.segments = {}

        self.frame_buffer = []

        self.buffer_lock = threading.Lock()
        self.buffer_abort: threading.Event = threading.Event()
        self.buffer_ready_condition = threading.Condition()
        self.buffer_thread = None

        self.ffmpeg_thread: threading.Thread = None
        self.ffmpeg_cmd_queue: queue.Queue = queue.Queue()
        self.ffmpeg_stop_when_jobs_complete_event: threading.Event = threading.Event()

        Path(staging_dir).mkdir(parents=True, exist_ok=True)
        self.staging_dir = staging_dir

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir

        self.frames_handled = 0
        self.frames_captured = 0

        self._current_clip_start_datetime: Optional[datetime] = None

        self.clip_duration = clip_duration
        self.encoder_monotonic_start_time_in_seconds: Optional[float] = None

        self.current_clip_frame_count = 0

        self.frame_rate = frame_rate
        self.gop_size = gop_size

        self.system_monotonic_datetime_start = datetime.fromtimestamp(
            time.clock_gettime(time.CLOCK_REALTIME)
            - time.clock_gettime(time.CLOCK_MONOTONIC)
        )
        self.is_initial_capture_loop_pass = False
        self.capture_start_monotonic_time_in_seconds = None
        self.initial_frame_timestamp_in_seconds_from_camera_init = None

    @property
    def current_clip_start_datetime(self):
        return self._current_clip_start_datetime

    @current_clip_start_datetime.setter
    def current_clip_start_datetime(self, value: Optional[datetime]):
        self._current_clip_start_datetime = value

    @property
    def loose_clip_start_datetime(self):
        return self.current_clip_start_datetime - timedelta(
            milliseconds=1000 / self.frame_rate
        )

    @property
    def current_clip_end_datetime(self):
        return self.current_clip_start_datetime + timedelta(seconds=self.clip_duration)

    @property
    def loose_clip_end_datetime(self):
        return self.current_clip_end_datetime + timedelta(
            milliseconds=1000 / self.frame_rate
        )

    def refresh_timeslot(self):
        self.current_clip_start_datetime = datetime.fromtimestamp(util.next_timeslot())

    def start(self):
        if self.buffer_thread is None:
            self.buffer_thread = threading.Thread(
                target=self.process_buffer,
                name="CameraOutputSegmenterFrameBuffer",
                daemon=False,
            )

        if self.buffer_thread.is_alive():
            logger.info(
                "Not starting the camera output segmenter, it's already running"
            )
        else:
            self.refresh_timeslot()
            self.buffer_thread.start()
            self.is_initial_capture_loop_pass = True

        if self.ffmpeg_thread is None:
            self.ffmpeg_thread = threading.Thread(
                target=self.process_ffmpeg_queue,
                name="CameraOutputSegmenterFFMpegProcessor",
                daemon=False,
            )
            self.ffmpeg_thread.start()

        super().start()
        logger.info(
            f"Camera output segmenter started if not already running, recording status is: {self.recording}"
        )

    def stop(self, keep_ffmpeg_running=True):
        logger.info("Attempting to stop camera output segmenter processing...")
        self.buffer_abort.set()
        with self.buffer_ready_condition:
            self.buffer_ready_condition.notify_all()
        if self.buffer_thread is not None and self.buffer_thread.is_alive():
            self.buffer_thread.join()

        self.buffer_abort.clear()
        self.buffer_thread = None
        self.frame_buffer = []
        self.segments = {}

        if keep_ffmpeg_running is False:
            logger.info(
                "Stopping ffmpeg processing thread, waiting for current jobs to finish..."
            )
            self.ffmpeg_stop_when_jobs_complete_event.set()
            self.ffmpeg_thread.join()
            self.ffmpeg_thread = None
            self.ffmpeg_stop_when_jobs_complete_event.clear()
            logger.info("Stopped ffmpeg thread")
        else:
            logger.info("Leaving ffmpeg thread running")

        super().stop()
        logger.info("Camera output segmenter processing stopped")

        self.is_initial_capture_loop_pass = False
        self.current_clip_start_datetime = None
        self.capture_start_monotonic_time_in_seconds = None
        self.initial_frame_timestamp_in_seconds_from_camera_init = None

    def process_buffer(self):
        logger.info(
            f"Starting processing buffer, next timeslot: {self.current_clip_start_datetime}"
        )
        while not self.buffer_abort.is_set():
            with self.buffer_ready_condition:
                self.buffer_ready_condition.wait()

            for filename_key in list(self.segments.keys()):
                segment = self.segments.get(filename_key)
                if segment.get("ready", False) == True:
                    logger.info(f"Processing '{segment['name']}' - Starting...")
                    logger.info(
                        f"Processing '{segment['name']}' - Segment spans '{segment['start_datetime']}' - '{segment['end_datetime']}'"
                    )
                    logger.info(
                        f"Processing '{segment['name']}' - Building video file..."
                    )
                    df_fitted_frames = None
                    with self.buffer_lock:
                        df_expected_times = pd.date_range(
                            start=segment["start_datetime"],
                            end=segment["end_datetime"]
                            - timedelta(milliseconds=1000 / self.frame_rate),
                            freq=f"{1000/self.frame_rate}L",
                        ).to_frame(index=False, name="frame_time")

                        df_captured_frames = pd.DataFrame(
                            self.frame_buffer
                        ).sort_values(by="image_timestamp")

                        df_fitted_frames = pd.merge_asof(
                            left=df_expected_times,
                            right=df_captured_frames,
                            left_on="frame_time",
                            right_on="image_timestamp",
                            allow_exact_matches=True,
                            direction="nearest",
                        )

                        # Cleanup the frame buffer
                        # (If mp4 supported negative PTS values, we could use this. But because it doesn't we only look ahead for frames)
                        # invalidate_timestamp = df_fitted_frames.iloc[-1]['image_timestamp']
                        invalidate_timestamp = segment["end_datetime"]
                        self.frame_buffer[:] = filterfalse(
                            lambda item: item["image_timestamp"] < invalidate_timestamp,
                            self.frame_buffer,
                        )

                    if df_fitted_frames is None:
                        continue

                    video_output = FileOutput(file=segment["staging_source_filepath"])
                    # output = FlexibleFfmpegOutput(output_filepath=segment['staging_mp4_filepath'])
                    video_output.start()

                    pts_file_path = Path(segment["staging_pts_filepath"])
                    Path.unlink(pts_file_path, missing_ok=True)
                    with pts_file_path.open(mode="w+", encoding="utf-8") as pts_file:
                        previous_pts = []
                        for idx, frame in df_fitted_frames.iterrows():
                            relative_pts = (
                                frame["image_timestamp"] - segment["start_datetime"]
                            ).total_seconds()

                            # There cannot be duplicate PTS times, if one occurs, add a slight offset
                            while relative_pts in previous_pts:
                                logger.info(
                                    f"Duplicate PTS value {relative_pts}, offsetting by 0.001"
                                )
                                relative_pts += 0.001

                            previous_pts.append(relative_pts)

                            if idx == 0:
                                pts_file.write("# timestamp format v2\n0\n")
                            else:
                                pts_file.write(f"{(relative_pts * 1000):.3f}\n")

                            video_output.outputframe(
                                frame=frame["data"],
                                keyframe=frame["keyframe"],
                                timestamp=relative_pts * 1e9,
                            )
                        # Warning! Frame manipulation devilry ahead!
                        # We're adding a final frame with a PTS time that EXACTLY represents the desired video duration
                        # We do this to manipulate the duration between the official final and the "devil" final frame
                        # Once ffmpeg creates our mp4, we will chop the devil frame and it will result in a video file that is EXACTLY the length we want
                        final_pts_in_seconds = self.clip_duration * 1.0
                        pts_file.write(f"{(final_pts_in_seconds * 1000):.3f}")
                        video_output.outputframe(
                            frame=df_fitted_frames.iloc[-1]["data"],
                            keyframe=df_fitted_frames.iloc[-1]["keyframe"],
                            timestamp=final_pts_in_seconds * 1e9,
                        )

                    video_output.stop()

                    logger.info(
                        f"Processing '{segment['name']}' - Video created! Total frames: {len(df_fitted_frames)}"
                    )

                    cmds = []
                    if isinstance(video_output, FileOutput):
                        logger.info(
                            f"Processing '{segment['name']}' - Converting mjpeg to mp4..."
                        )
                        # Very important: using h264_v4l2m2m for hardware acceleration
                        cmds.append(
                            [
                                "ffmpeg",
                                "-f",
                                "mjpeg",
                                "-r",
                                f"{self.frame_rate}",
                                "-hide_banner",
                                "-loglevel",
                                "warning",
                                "-y",
                                "-thread_queue_size",
                                "32",
                                "-i",
                                f"{segment['staging_source_filepath']}",
                                "-pix_fmt",
                                "yuv420p",
                                "-b:v",
                                "3M",
                                "-c:v",
                                "h264_v4l2m2m",
                                "-g",
                                f"{self.gop_size}",
                                "-keyint_min",
                                f"{self.gop_size}",
                                "-sc_threshold",
                                "0",
                                "-f",
                                "mp4",
                                f"{segment['staging_mp4_filepath']}",
                            ]
                        )

                    # Sleep because the mp4 file isn't quite ready for some reason...
                    cmds.append(["sleep", "1"])
                    cmds.append(
                        [
                            "mv",
                            segment["staging_mp4_filepath"],
                            f"{segment['staging_mp4_filepath']}.tmp",
                        ]
                    )
                    # Next step is to update the PTS timestamps. We use mp4fpsmod
                    cmds.append(
                        [
                            "mp4fpsmod",
                            "-t",
                            f"{segment['staging_pts_filepath']}",
                            f"{segment['staging_mp4_filepath']}.tmp",
                            "-o",
                            f"{segment['staging_mp4_filepath']}.mp4fpsmod.tmp",
                        ]
                    )
                    # Now chop the final "devil" frame and output the mp4 to its final destination
                    cmds.append(
                        [
                            "ffmpeg",
                            "-y",
                            "-hide_banner",
                            "-loglevel",
                            "warning",
                            "-i",
                            f"{segment['staging_mp4_filepath']}.mp4fpsmod.tmp",
                            "-frames:v",
                            f"{self.clip_duration * self.frame_rate}",
                            "-c:v",
                            "copy",
                            f"{segment['final_mp4_filepath']}",
                        ]
                    )

                    # mkvmerge example - Note, I couldn't get mkvmerge to work with mp4s. I needed to convert it to an mkv which added an extra step
                    # cmds.append(f"mkvmerge -o {segment['mp4_filepath']} --timestamps 0:{segment['pts_filepath']} {segment['mp4_filepath']}.tmp")
                    # Finally cleanup, cleanup, everybody cleanup
                    cmds.append(
                        [
                            "rm",
                            "-f",
                            f"{segment['staging_pts_filepath']}",
                            f"{segment['staging_mp4_filepath']}.mp4fpsmod.tmp",
                            f"{segment['staging_mp4_filepath']}.tmp",
                            f"{segment['staging_source_filepath']}",
                        ]
                    )

                    self.ffmpeg_cmd_queue.put(
                        item={
                            "cmds": cmds,
                            "name": segment["name"],
                            "in_file": segment["staging_source_filepath"],
                            "out_file": segment["final_mp4_filepath"],
                        },
                        block=False,
                    )

                    self.segments.pop(filename_key)

        logger.info("Stopped processing buffer")

    def process_ffmpeg_queue(self):
        while True:
            try:
                job = self.ffmpeg_cmd_queue.get(block=True, timeout=0.3)
            except queue.Empty:
                if self.ffmpeg_stop_when_jobs_complete_event.is_set():
                    break

                continue

            try:
                logger.info(
                    f"Current ffmpeg job queue size (not including active job): {self.ffmpeg_cmd_queue.qsize()}"
                )

                logger.info(
                    f"Processing '{job['name']}' - Converting mjpeg file '{job['in_file']}' to mp4 '{job['out_file']}'..."
                )
                for cmd in job["cmds"]:
                    proc = subprocess.Popen(
                        args=cmd,
                        shell=False,
                        stdin=subprocess.PIPE,
                        preexec_fn=lambda: prctl.set_pdeathsig(signal.SIGKILL),
                    )
                    proc.wait()
                logger.info(
                    f"Processing '{job['name']}' - Finished converting '{job['in_file']}' file to '{job['out_file']}'"
                )
            finally:
                self.ffmpeg_cmd_queue.task_done()

        logger.info("Stopping ffmpeg processor thread")

    def current_filename(self, format: str = None):
        return util.video_clip_name(
            clip_datetime=self.current_clip_start_datetime, format=format
        )

    def current_filepath(self, output_dir: str = ".", format: str = None):
        return f"{output_dir}/{self.current_filename(format=format)}"

    def rotate(self):
        current_filename = self.current_filename(format="")
        segment = self.segments.get(current_filename, None)
        if segment is not None:
            segment["ready"] = True

            logger.info("Triggering buffer flush")
            with self.buffer_ready_condition:
                self.buffer_ready_condition.notify_all()

        self.current_clip_start_datetime = self.current_clip_end_datetime
        self.current_clip_frame_count = 0

    def set_encoder_monotonic_start_time(self, encoder_monotonic_start_time):
        self.encoder_monotonic_start_time_in_seconds = encoder_monotonic_start_time

    def outputframe(self, frame, keyframe=True, timestamp=None):
        if not self.recording:
            logger.warning(
                "Attempting to output frame to the output segmenter, but the output segmenter is not recording"
            )
            return

        output_processed_timestamp = datetime.now()
        self.frames_handled += 1

        frame_timestamp_in_seconds_from_camera_init = 0
        if timestamp > 0:
            frame_timestamp_in_seconds_from_camera_init = timestamp / 1e6

        image_timestamp = self.system_monotonic_datetime_start + timedelta(
            seconds=self.encoder_monotonic_start_time_in_seconds
            + frame_timestamp_in_seconds_from_camera_init
        )

        if image_timestamp >= self.loose_clip_end_datetime:
            self.rotate()

        valid_time = image_timestamp >= self.loose_clip_start_datetime
        if valid_time:
            self.current_clip_frame_count += 1
            self.frames_captured += 1

            with self.buffer_lock:
                self.frame_buffer.append(
                    {
                        "image_timestamp": image_timestamp,
                        "timestamp": timestamp,
                        "keyframe": keyframe,
                        "data": frame,
                    }
                )

            current_filename_no_format = self.current_filename(format="")
            segment = self.segments.get(current_filename_no_format, None)
            if segment is None:
                segment = {
                    "name": self.current_filename(format="mp4"),
                    "staging_source_filepath": self.current_filepath(
                        output_dir=self.staging_dir, format="mjpeg"
                    ),
                    "staging_mp4_filepath": self.current_filepath(
                        output_dir=self.staging_dir, format="mp4"
                    ),
                    "staging_pts_filepath": self.current_filepath(
                        output_dir=self.staging_dir, format="pts"
                    ),
                    "final_mp4_filepath": self.current_filepath(
                        output_dir=self.output_dir, format="mp4"
                    ),
                    "start_datetime": self.current_clip_start_datetime,
                    "end_datetime": self.current_clip_end_datetime,
                    "frames": [],
                    "ready": False,
                }
                self.segments[current_filename_no_format] = segment

        if self.is_initial_capture_loop_pass:
            self.capture_start_monotonic_time_in_seconds = time.clock_gettime(
                time.CLOCK_MONOTONIC
            )
            self.initial_frame_timestamp_in_seconds_from_camera_init = timestamp / 1e6

        log_message = f"Frames Handled: {self.frames_handled} | Frames Captured: {self.frames_captured} | Frames in Current Clip: {self.current_clip_frame_count} | Include: {valid_time} | Current Time: {output_processed_timestamp.strftime('%H:%M:%S.%f')[:-3]} | Frame Inferred Timestamp: {image_timestamp.strftime('%H:%M:%S.%f')[:-3]} | Frame Processing Delay: {(output_processed_timestamp - image_timestamp).total_seconds()} | Frame Seconds from Camera Start: {frame_timestamp_in_seconds_from_camera_init} | System Time Progression Since Capture Start {(time.clock_gettime(time.CLOCK_MONOTONIC) - self.capture_start_monotonic_time_in_seconds):.3f} | Frame Time Progression Since Capture Start {(frame_timestamp_in_seconds_from_camera_init - self.initial_frame_timestamp_in_seconds_from_camera_init):.3f} | Keyframe: {keyframe} | Clip Start {self.current_clip_start_datetime} |  Clip End {self.current_clip_end_datetime} | Buffer Size {len(self.frame_buffer)}"
        if logger.level == logging.DEBUG:
            logger.debug(log_message)
        elif (
            self.is_initial_capture_loop_pass
            or self.frames_handled == 1
            or (self.frames_handled % 1000) == 0
        ):
            logger.info(log_message)

        self.is_initial_capture_loop_pass = False
