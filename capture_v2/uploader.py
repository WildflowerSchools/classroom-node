import psutil
import time

from minio import Minio
from minio.error import MinioException
import os
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileCreatedEvent, PatternMatchingEventHandler

from . import util
from .config import Settings
from .log import logger


class MinioVideoUploader:
    def __init__(
        self,
        output_dir: str,
        video_clip_duration: int = 10,
        remove_video_after_upload: bool = False,
    ):
        self.video_clip_duration = video_clip_duration
        self.output_dir = output_dir
        self.remove_video_after_upload = remove_video_after_upload

        settings = Settings()
        self.MINIO_SERVICE_HOST = settings.MINIO_SERVICE_HOST
        self.MINIO_SERVICE_PORT = str(settings.MINIO_SERVICE_PORT)
        self.MINIO_KEY = settings.MINIO_KEY
        self.MINIO_SECRET = settings.MINIO_SECRET
        self.MINIO_BUCKET = settings.MINIO_BUCKET
        self.MINIO_FOLDER = settings.MINIO_FOLDER

        self.client = self._init_client()
        self.observer = None
        self.event_handler = None

    def _init_client(self):
        host = self.MINIO_SERVICE_HOST
        port = self.MINIO_SERVICE_PORT
        client = Minio(
            endpoint=":".join([host, port]),
            access_key=self.MINIO_KEY,
            secret_key=self.MINIO_SECRET,
            secure=False,
        )

        if not client.bucket_exists(self.MINIO_BUCKET):
            try:
                client.make_bucket(self.MINIO_BUCKET, location="us-east-1")
            except MinioException as e:
                logger.exception(e)
                raise e

        return client

    def on_video_file_created(self, event):
        video_path = Path(event.src_path)
        video_filename = video_path.name
        video_datetime = util.get_datetime_from_video_clip_name(video_filename)
        if video_datetime is None:
            logger.warning(
                f"Unexpected video file detected ('unexpected' based on filename format) in the upload folder: {video_path}"
            )
            return

        # Wait for all handles on the file to be relinquished
        total_sleep = 0
        while util.does_file_have_handle(video_path.resolve()):
            sleep = 0.2
            time.sleep(sleep)
            total_sleep += sleep
            if total_sleep > 10:
                logger.error(
                    f"Unable to upload '{video_path.resolve()}' to minio. Waited {total_sleep} seconds, but handles on file were never relinquished."
                )
                return

        ts = util.video_clip_datetime_to_filename_date_format(video_datetime)

        obj_parts = [self.MINIO_FOLDER, f"{ts.replace('_', '/')}.mp4"]
        obj_name = "/".join(filter(lambda p: p is not None and p != "", obj_parts))
        logger.info(
            f"Uploading video '{event.src_path}' to minio. Storing as '{obj_name}'..."
        )
        self.client.fput_object(
            bucket_name=self.MINIO_BUCKET,
            object_name=obj_name,
            file_path=video_path.resolve(),
            content_type="video/mp4",
            metadata={
                "source": self.MINIO_FOLDER,
                "ts": ts,
                "duration": f"{self.video_clip_duration}s",
            },
        )
        logger.info(
            f"Minio '{obj_name}' upload successful.",
            extra={"metric_tag": "video_moved", "video_start_time": ts},
        )

        if self.remove_video_after_upload:
            try:
                logger.info(f"Removing '{event.src_path}' after successful upload")
                os.remove(video_path.resolve())
            except FileNotFoundError:
                logger.warning(f"Couldn't remove '{event.src_path}', file disappeared?")
                pass  # file disappeared?

    def flush_existing_videos_on_disk(self):
        for item in os.listdir(self.output_dir):
            if item.endswith(".mp4"):
                video_path = f"/{self.output_dir}/{item}"
                synthetic_event = FileCreatedEvent(src_path=video_path)
                synthetic_event.is_synthetic = True
                self.event_handler.dispatch(event=synthetic_event)

    def start(self):
        self.event_handler = PatternMatchingEventHandler(
            patterns=["*.mp4"], ignore_directories=True, case_sensitive=False
        )
        self.event_handler.on_created = self.on_video_file_created

        self.observer = Observer()
        self.observer.schedule(
            event_handler=self.event_handler, path=self.output_dir, recursive=False
        )
        self.observer.start()

        self.flush_existing_videos_on_disk()

    def stop(self):
        if self.observer and self.observer.is_alive():
            self.observer.stop()
            self.observer.join()
            self.event_handler = None
            self.observer = None
