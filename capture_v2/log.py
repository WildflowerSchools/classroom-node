import logging
from logging.config import dictConfig
import os


from pydantic import BaseModel


class LogConfig(BaseModel):
    """Logging configuration to be set for the server"""

    LOGGER_NAME: str = "wf_camera_processor"
    LOG_FORMAT: str = "%(asctime)s,%(msecs)03d | %(levelname)s | %(name)s | %(message)s"
    LOG_LEVEL: str = (
        "DEBUG" if os.getenv("DEBUG", "False").lower() in ("true", "1", "t") else "INFO"
    )

    # Logging config
    version = 1
    disable_existing_loggers = False
    formatters = {
        "default": {
            "format": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    }
    loggers = {
        LOGGER_NAME: {"handlers": ["default"], "level": LOG_LEVEL, "propagate": False},
    }


dictConfig(LogConfig().dict())
logger = logging.getLogger("wf_camera_processor")
