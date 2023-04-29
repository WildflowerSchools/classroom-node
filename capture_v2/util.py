from datetime import datetime
import re
import time
from typing import Optional

from .config import Settings


def next_timeslot():
    settings = Settings()

    now = time.time()
    return now + (settings.VIDEO_CLIP_DURATION - (now % settings.VIDEO_CLIP_DURATION))


def video_clip_datetime_to_filename_date_format(clip_datetime: datetime):
    return f"{clip_datetime:%Y_%m_%d_%H_%M-%S}"


def video_clip_name(clip_datetime: datetime, format: Optional[str] = "mp4"):
    extension = f".{format}"
    if format is None or format == "":
        extension = ""

    return (
        f"video-{video_clip_datetime_to_filename_date_format(clip_datetime)}{extension}"
    )


def split_video_clip_file_name(filename: str = "", format: str = "mp4"):
    # Example filename: video-2023_04_28_18_53-10.mp4
    pattern = rf"video-(\d{{4}}_\d{{2}}_\d{{2}}_\d{{2}}_\d{{2}}-\d{{2}}).{format}"
    return re.match(pattern, filename)


def does_filename_match_video_clip_format(filename: str = ""):
    return split_video_clip_file_name(filename) is not None


def get_datetime_from_video_clip_name(filename: str = ""):
    if not does_filename_match_video_clip_format(filename):
        return None

    video_clip_datetime_as_str = split_video_clip_file_name(filename)[1]
    return datetime.strptime(video_clip_datetime_as_str, "%Y_%m_%d_%H_%M-%S")
