import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import time

from influx_line_protocol import Metric


def get_logger(name):
    logger = logging.getLogger("wf_metrics")
    METRICS_LOG_DIR = Path(os.environ.get("METRICS_LOG", "./wf_metrics"))
    if not METRICS_LOG_DIR.exists():
        METRICS_LOG_DIR.mkdir()
    path = METRICS_LOG_DIR / f"{name}.log"
    logger.setLevel(logging.INFO)
    handy = RotatingFileHandler(path, maxBytes=20000000, backupCount=5)
    handy.setFormatter(logging.Formatter())
    logger.addHandler(handy)
    return logger


metric = Metric("weather")
metric.with_timestamp(time.time() * 1000000000)
metric.add_tag('location', 'Cracow')
metric.add_value('temperature', '29')

logger.info(metric)
