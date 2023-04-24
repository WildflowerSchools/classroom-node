from datetime import datetime, timedelta
from itertools import filterfalse
from pathlib import Path
import subprocess
from threading import Condition, Lock, Thread
import time

from picamera2.outputs import FileOutput, FfmpegOutput

import pandas as pd

from .flexible_ffmpeg_output import FlexibleFfmpegOutput
from .log import logger


class CameraOutputSegmenter(FileOutput):
    def __init__(
        self,
        start_datetime: datetime,
        end_datetime: datetime = None,
        clip_duration: int = 10,  # in seconds
        frame_rate: int = 10,
        pts=None,
        output_dir=".",
    ):
        super().__init__(pts=pts)
        self.segments = {}

        self.frame_buffer = []

        self.buffer_lock = Lock()
        self.buffer_abort = False
        self.buffer_ready_condition = Condition()
        self.buffer_thread = Thread(target=self.process_buffer, daemon=True)
        self.buffer_thread.start()

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        self.output_dir = output_dir

        self.frames_handled = 0
        self.frames_captured = 0

        self.start_datetime = start_datetime
        self.end_datetime = end_datetime

        self.clip_start_datetime = start_datetime
        self.clip_end_datetime = start_datetime + timedelta(seconds=clip_duration)
        self.clip_duration = clip_duration
        self.current_clip_frame_count = 0

        self.frame_rate = frame_rate

        self.monotonic_datetime_start = datetime.fromtimestamp(
            time.clock_gettime(time.CLOCK_REALTIME)
            - time.clock_gettime(time.CLOCK_MONOTONIC)
        )
        self.end_time_eclipsed = False

    def stop(self, wait=True):
        logger.info("Attempting to stop camera output processing thread...")
        self.buffer_abort = True
        with self.buffer_ready_condition:
            self.buffer_ready_condition.notify_all()
        self.buffer_thread.join()
        logger.info("Camera output processing thread stopped")

    def process_buffer(self):
        logger.info("Starting processing buffer")
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

                        df_captured_frames = pd.DataFrame(self.frame_buffer)

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

                    output = FileOutput(file=segment["source_filepath"])
                    # output = FlexibleFfmpegOutput(output_filepath=segment['mp4_filepath'])#segment['mp4_filepath'])
                    output.start()

                    pts_file_path = Path(segment["pts_filepath"])
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

                            output.outputframe(
                                frame=frame["data"],
                                keyframe=frame["keyframe"],
                                timestamp=relative_pts * 1e9,
                            )

                    output.stop()

                    logger.info(
                        f"Processing '{segment['name']}' - Video created! Total frames: {len(df_fitted_frames)}"
                    )

                    cmds = []
                    if isinstance(output, FileOutput):
                        logger.info(
                            f"Processing '{segment['name']}' - Converting mjpeg to mp4..."
                        )
                        cmds.append(
                            f"ffmpeg -f mjpeg -r {self.frame_rate} -loglevel warning -y -thread_queue_size 32 -i {segment['source_filepath']} -pix_fmt yuv420p -b:v 4M -c:v h264_v4l2m2m -f mp4 {segment['mp4_filepath']}"
                        )

                    cmds.append(
                        f"sleep 1"
                    )  # The mp4 file isn't quite ready it seems...
                    cmds.append(
                        f"mv {segment['mp4_filepath']} {segment['mp4_filepath']}.tmp"
                    )
                    # Next step is to update the PTS timestamps. We use mp4fpsmod
                    cmds.append(
                        f"mp4fpsmod -t {segment['pts_filepath']} {segment['mp4_filepath']}.tmp -o {segment['mp4_filepath']}"
                    )
                    # mkvmerge example - Note, I couldn't get mkvmerge to work with mp4s. I needed to convert it to an mkv which added an extra step
                    # cmds.append(f"mkvmerge -o {segment['mp4_filepath']} --timestamps 0:{segment['pts_filepath']} {segment['mp4_filepath']}.tmp")
                    # Finally cleanup, cleanup, everybody cleanup
                    cmds.append(
                        f"rm -f {segment['pts_filepath']} {segment['mp4_filepath']}.tmp {segment['source_filepath']}"
                    )

                    def popen_and_call(on_exit, popen_args):
                        """
                        Thanks @Daniel G: https://stackoverflow.com/a/2581943/17081132

                        I added this so we could trigger a callback when the cmd line script ends. In our case, I wanted to pring a simple message to stdout.
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

                    thread_safe_callback = lambda msg: lambda: logger.info(msg)
                    done_msg = f"Processing '{segment['name']}' - Done. Video file path: '{segment['mp4_filepath']}'"
                    popen_and_call(
                        thread_safe_callback(done_msg),
                        {"args": "; ".join(cmds.copy()), "shell": True},
                    )

                    self.segments.pop(filename_key)

    def current_filename(self, format: str = None):
        return f"video-{self.clip_start_datetime:%Y_%m_%d_%H_%M-%S}.{format}"

    def current_filepath(self, format: str = None):
        return f"{self.output_dir}/{self.current_filename(format=format)}"

    def rotate(self):
        current_filepath = self.current_filepath(format="")
        segment = self.segments.get(current_filepath, None)
        if segment is not None:
            segment["ready"] = True

            logger.info("Triggering buffer flush")
            with self.buffer_ready_condition:
                self.buffer_ready_condition.notify_all()

        self.clip_start_datetime = self.clip_end_datetime
        self.clip_end_datetime = self.clip_end_datetime + timedelta(
            seconds=self.clip_duration
        )
        self.current_clip_frame_count = 0

    def set_camera_monotonic_start_time(self, camera_monotonic_start_time):
        self.camera_monotonic_start_time_in_seconds = camera_monotonic_start_time

    def outputframe(self, frame, keyframe=True, timestamp=None):
        loose_start_datetime = self.start_datetime - timedelta(
            milliseconds=1000 / self.frame_rate
        )
        loose_end_datetime = None
        if self.end_datetime:
            loose_end_datetime = self.end_datetime + timedelta(
                milliseconds=1000 / self.frame_rate
            )

        loose_clip_end_datetime = self.clip_end_datetime + timedelta(
            milliseconds=1000 / self.frame_rate
        )

        self.frames_handled += 1

        frame_timestamp_in_seconds_from_init = 0
        if timestamp > 0:
            frame_timestamp_in_seconds_from_init = timestamp / 1e6

        # If the monotonic start time is the time we get for the first photo, then we might want to subtract that value, not add it
        image_timestamp = self.monotonic_datetime_start + timedelta(
            seconds=self.camera_monotonic_start_time_in_seconds
            + frame_timestamp_in_seconds_from_init
        )

        if loose_end_datetime is not None and image_timestamp >= loose_end_datetime:
            if not self.end_time_eclipsed:
                self.rotate()
                self.end_time_eclipsed = True
        if image_timestamp >= loose_clip_end_datetime:
            if not self.end_time_eclipsed:
                self.rotate()

        valid_time = image_timestamp >= loose_start_datetime and (
            loose_end_datetime is None
            or (loose_end_datetime is not None and image_timestamp < loose_end_datetime)
        )
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

            current_filepath = self.current_filepath(format="")
            segment = self.segments.get(current_filepath, None)
            if segment is None:
                segment = {
                    "name": self.current_filename(format="mp4"),
                    "source_filepath": self.current_filepath(format="mjpeg"),
                    "mp4_filepath": self.current_filepath(format="mp4"),
                    "pts_filepath": self.current_filepath(format="pts"),
                    "start_datetime": self.clip_start_datetime,
                    "end_datetime": self.clip_end_datetime,
                    "frames": [],
                    "ready": False,
                }
                self.segments[current_filepath] = segment

        logger.debug(
            f"Frames handled: {self.frames_handled} | Frames captured: {self.frames_captured} | Frames in current clip: {self.current_clip_frame_count} | Include: {valid_time} | Current Time: {datetime.now().strftime('%M:%S.%f')[:-3]} | Frame Timestamp: {image_timestamp.strftime('%M:%S.%f')[:-3]} | Seconds: {frame_timestamp_in_seconds_from_init} | Keyframe: {keyframe} | Clip Start {self.clip_start_datetime} |  Clip End {self.clip_end_datetime} | Buffer size {len(self.frame_buffer)}"
        )
