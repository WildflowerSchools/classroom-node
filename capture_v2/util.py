import time

from .config import Settings


def next_timeslot():
    settings = Settings()

    now = time.time()
    return now + (settings.VIDEO_CLIP_DURATION - (now % settings.VIDEO_CLIP_DURATION))
