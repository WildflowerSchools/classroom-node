from datetime import datetime


ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
ISO_FORMAT_SHORT = "%Y-%m-%dT%H:%M:%S"


def now(short=False):
    if short:
        return datetime.utcnow().strftime(ISO_FORMAT)
    else:
        return datetime.utcnow().strftime(ISO_FORMAT_SHORT)
