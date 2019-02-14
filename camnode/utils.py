from datetime import datetime


ISO_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"

def now():
    return datetime.utcnow().strftime(ISO_FORMAT)
