from datetime import datetime, timedelta
from itertools import filterfalse
import logging
from pathlib import Path
import subprocess
from threading import Condition, Lock, Thread
import time
from typing import Optional

from picamera2.outputs import Output, FileOutput

import pandas as pd

from capture_v2 import util
from capture_v2.log import logger


class CameraOutputSegmenter(Output):
    def __init__(
        self,
        # start_datetime: datetime,
        # end_datetime: datetime = None,
        # stop_recording_when_end_datetime_eclipsed: bool = True,
        clip_duration: int = 10,  # in seconds
        frame_rate: int = 10,
        pts=None,
        staging_dir="./staging",
        output_dir="./output",
        finalize_video_in_background=False,
    ):
        super().__init__(pts=pts)
        self.segments = {}

        self.frame_buffer = []

        self.buffer_lock = Lock()
        self.buffer_abort = False
        self.buffer_ready_condition = Condition()
        self.buffer_thread = None

        Path(staging_dir).mkdir(parents=True, exist_ok=True)
        self.staging_dir = staging_dir

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir

        self.finalize_video_in_background = finalize_video_in_background

        self.frames_handled = 0
        self.frames_captured = 0

        self._current_clip_start_datetime: Optional[datetime] = None

        self.clip_duration = clip_duration
        self.camera_monotonic_start_time_in_seconds: Optional[datetime] = None

        self.current_clip_frame_count = 0

        self.frame_rate = frame_rate

        self.monotonic_datetime_start = datetime.fromtimestamp(
            time.clock_gettime(time.CLOCK_REALTIME)
            - time.clock_gettime(time.CLOCK_MONOTONIC)
        )

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
            self.buffer_thread = Thread(target=self.process_buffer, daemon=False)

        if self.buffer_thread.is_alive():
            logger.info(
                "Not starting the camera output segmenter, it's already running"
            )
        else:
            self.refresh_timeslot()
            self.buffer_thread.start()

        super().start()

    def stop(self, wait=True):
        logger.info("Attempting to stop camera output segmenter processing...")
        self.buffer_abort = True
        with self.buffer_ready_condition:
            self.buffer_ready_condition.notify_all()
        if self.buffer_thread.is_alive():
            self.buffer_thread.join()

        self.buffer_abort = False
        self.buffer_thread = None
        self.frame_buffer = []
        self.segments = {}

        super().stop()
        logger.info("Camera output segmenter processing stopped")
        self.current_clip_start_datetime = None

    def process_buffer(self):
        logger.info(
            f"Starting processing buffer, next timeslot: {self.current_clip_start_datetime}"
        )
        while not self.buffer_abort:
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
                        for idx, frame in df_fitted_frames.iterrows():
                            relative_pts = (
                                frame["image_timestamp"] - segment["start_datetime"]
                            ).total_seconds()
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
                            f"ffmpeg -f mjpeg -r {self.frame_rate} -hide_banner -loglevel warning -y -thread_queue_size 32 -i {segment['staging_source_filepath']} -pix_fmt yuv420p -b:v 4M -c:v h264_v4l2m2m -f mp4 {segment['staging_mp4_filepath']}"
                        )

                    # Sleep because the mp4 file isn't quite ready for some reason...
                    cmds.append(f"sleep 1")
                    cmds.append(
                        f"mv {segment['staging_mp4_filepath']} {segment['staging_mp4_filepath']}.tmp"
                    )
                    # Next step is to update the PTS timestamps. We use mp4fpsmod
                    cmds.append(
                        f"mp4fpsmod -t {segment['staging_pts_filepath']} {segment['staging_mp4_filepath']}.tmp -o {segment['staging_mp4_filepath']}.mp4fpsmod.tmp"
                    )
                    # Now chop the final "devil" frame and output the mp4 to its final destination
                    cmds.append(
                        f"ffmpeg -y -hide_banner -loglevel warning -i {segment['staging_mp4_filepath']}.mp4fpsmod.tmp -frames:v {self.clip_duration * self.frame_rate} -c:v copy {segment['final_mp4_filepath']}"
                    )

                    # mkvmerge example - Note, I couldn't get mkvmerge to work with mp4s. I needed to convert it to an mkv which added an extra step
                    # cmds.append(f"mkvmerge -o {segment['mp4_filepath']} --timestamps 0:{segment['pts_filepath']} {segment['mp4_filepath']}.tmp")
                    # Finally cleanup, cleanup, everybody cleanup
                    cmds.append(
                        f"rm -f {segment['staging_pts_filepath']} {segment['staging_mp4_filepath']}.mp4fpsmod.tmp {segment['staging_mp4_filepath']}.tmp {segment['staging_source_filepath']}"
                    )

                    def popen_and_call(on_exit, popen_args):
                        """
                        Thanks @Daniel G: https://stackoverflow.com/a/2581943/17081132

                        I added this so we could trigger a callback when the cmd line script ends. In our case, I wanted to print a simple message to stdout.
                        """

                        def run_in_thread(on_exit, popen_args):
                            proc = subprocess.Popen(**popen_args)
                            proc.wait()
                            on_exit()
                            return

                        thread = Thread(
                            target=run_in_thread, args=(on_exit, popen_args)
                        )
                        thread.start()
                        return thread

                    try:
                        _popen_args = {"args": "; ".join(cmds.copy()), "shell": True}
                        done_msg = f"Processing '{segment['name']}' - Done. Video file path: '{segment['final_mp4_filepath']}'"
                        if self.finalize_video_in_background:
                            thread_safe_callback = lambda msg: lambda: logger.info(msg)
                            popen_and_call(
                                on_exit=thread_safe_callback(done_msg),
                                popen_args=_popen_args,
                            )
                        else:
                            proc = subprocess.Popen(**_popen_args)
                            proc.wait()
                            logger.info(done_msg)
                    except Exception as e:
                        logger.error(f"Failed preparing '{segment['name']}': {e}")

                    self.segments.pop(filename_key)

        logger.info("Stopped processing buffer")

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

    def set_camera_monotonic_start_time(self, camera_monotonic_start_time):
        self.camera_monotonic_start_time_in_seconds = camera_monotonic_start_time

    def outputframe(self, frame, keyframe=True, timestamp=None):
        self.frames_handled += 1

        frame_timestamp_in_seconds_from_init = 0
        if timestamp > 0:
            frame_timestamp_in_seconds_from_init = timestamp / 1e6

        image_timestamp = self.monotonic_datetime_start + timedelta(
            seconds=self.camera_monotonic_start_time_in_seconds
            + frame_timestamp_in_seconds_from_init
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

        log_message = f"Frames handled: {self.frames_handled} | Frames captured: {self.frames_captured} | Frames in current clip: {self.current_clip_frame_count} | Include: {valid_time} | Current Time: {datetime.now().strftime('%M:%S.%f')[:-3]} | Frame Timestamp: {image_timestamp.strftime('%M:%S.%f')[:-3]} | Seconds: {frame_timestamp_in_seconds_from_init} | Keyframe: {keyframe} | Clip Start {self.current_clip_start_datetime} |  Clip End {self.current_clip_end_datetime} | Buffer size {len(self.frame_buffer)}"
        if logger.level == logging.DEBUG:
            logger.debug(log_message)
        else:
            if self.frames_handled == 1 or (self.frames_handled % 1000) == 0:
                logger.info(log_message)
