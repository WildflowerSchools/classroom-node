import datetime
import logging
from logging.handlers import RotatingFileHandler
from multiprocessing import Process, Queue
import os
from pathlib import Path
import time

import yaml
from minio import Minio
from minio.error import MinioException
from pythonjsonlogger import jsonlogger
from influx_line_protocol import Metric

logger = logging.getLogger()


logger.setLevel(level=logging.DEBUG)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(levelname)s %(asctime)s %(filename)s %(funcName)s %(message)s')
logHandler.setFormatter(formatter)
logger.addHandler(logHandler)


try:
    import picamera
except ImportError:
    logger.warning("picamera not available")

import ffmpeg


with open('/boot/wildflower-config.yml', 'r', encoding="utf-8") as fp:
    config = yaml.safe_load(fp.read())


DEVICE_ID = config.get("device_id", "unknown")
BUCKET = os.environ.get("MINIO_BUCKET_NAME", "videos")

CAMERA_RES = (os.environ.get("CAMERA_RES_W", 1296), os.environ.get("CAMERA_RES_H", 972))
CAMERA_FRAMERATE = os.environ.get("CAMERA_FRAMERATE", 10)
INTRA_PERIOD = os.environ.get("INTRA_PERIOD", 120)
BITRATE = os.environ.get("BITRATE", 1000000)
PERIOD = os.environ.get("DURATION", 10)
CAMERA_ISO_SETTING = int(os.environ.get("CAMERA_ISO_SETTING", 400))
CAMERA_EXPOSURE_MODE = os.environ.get("CAMERA_EXPOSURE_MODE", 'sports')
CAMERA_SHUTTER_SPEED = int(os.environ.get("CAMERA_SHUTTER_SPEED", 0))
CAMERA_H_FLIP = os.environ.get("CAMERA_H_FLIP", 0)
CAMERA_V_FLIP = os.environ.get("CAMERA_V_FLIP", 0)
METRICS_LOG_DIR = Path(os.environ.get("METRICS_LOG", "/var/log/wf_metrics"))

def get_logger(name):
    metlogger = logging.getLogger("wf_metrics")
    if not METRICS_LOG_DIR.exists():
        METRICS_LOG_DIR.mkdir()
    path = METRICS_LOG_DIR / f"{name}.log"
    metlogger.setLevel(logging.INFO)
    handy = RotatingFileHandler(path, maxBytes=20000000, backupCount=5)
    handy.setFormatter(logging.Formatter())
    metlogger.addHandler(handy)
    return metlogger

def emit(metlog, name, values, tags=None):
    metric = Metric(name)
    metric.with_timestamp(time.time() * 1000000000)
    if tags is None:
        tags = {"tag": "team"}
    for tag in tags:
        metric.add_tag(tag, tags[tag])
    for value in values:
        metric.add_value(value, values[value])
    metlog.info(metric)


def next_timeslot(now):
    return now + (PERIOD - (now % PERIOD))


def capture_loop():
    logger.setLevel(level=logging.DEBUG)
    logger.info("starting capture")
    try:
        with picamera.PiCamera() as camera:
            camera.resolution = CAMERA_RES
            camera.framerate = CAMERA_FRAMERATE
            camera.iso = CAMERA_ISO_SETTING
            camera.exposure_mode = CAMERA_EXPOSURE_MODE
            camera.shutter_speed = CAMERA_SHUTTER_SPEED
            logger.info("period is %s", PERIOD)
            camera.hflip = CAMERA_H_FLIP == "yes"
            camera.vflip = CAMERA_V_FLIP == "yes"

            now = time.time()
            timeslot = next_timeslot(now)
            sleep_time = timeslot - now

            if sleep_time < 2:  # Ensure camera has enough time to adjust
                sleep_time += PERIOD
                timeslot += PERIOD
            logger.info("going to sleep for a bit %s", sleep_time)
            time.sleep(sleep_time)
            metlog = get_logger("capture_loop")
            video_start_time = datetime.datetime.fromtimestamp(timeslot)
            name = f'/out/video-{video_start_time:%Y_%m_%d_%H_%M-%S}.h264'
            camera.start_recording(name, format='h264', intra_period=INTRA_PERIOD, bitrate=BITRATE)
            emit(metlog, "camera_capture", {"video_start": 1, "origin": 1, "split": 0})
            camera.wait_recording(PERIOD - 0.001)
            while True:
                timeslot += PERIOD
                video_start_time = datetime.datetime.fromtimestamp(timeslot)
                name = f'/out/video-{video_start_time:%Y_%m_%d_%H_%M-%S}.h264'
                logger.info("recording started", extra={"metric_tag": "video_start", "video_start_time": f"{video_start_time:%Y_%m_%d_%H_%M-%S}"})
                emit(metlog, "camera_capture", {"video_start": 1, "origin": 0, "split": 1})
                camera.split_recording(name, format='h264', intra_period=INTRA_PERIOD, bitrate=BITRATE)
                delay = timeslot + PERIOD - time.time()
                logger.info("waiting %s", delay)
                camera.wait_recording(delay)
    except Exception as e:
        logger.error(e)


def get_next_file():
    for item in os.listdir('/out'):
        if item.endswith(".h264"):
            fname = f'/out/{item}'
            st = os.stat(fname)
            if (time.time() - st.st_mtime) > 11 and st.st_size > 10000:
                return fname
    return None


def minio_client():
    KEY = os.environ.get("MINIO_KEY", "wildflower-classroom")
    SECRET = os.environ.get("MINIO_SECRET")
    if "MINIO_SERVICE_HOST" in os.environ:
        HOST = os.environ["MINIO_SERVICE_HOST"]
        PORT = os.environ["MINIO_SERVICE_PORT"]
        return  Minio(
                    ":".join([HOST, PORT]),
                    access_key=KEY,
                    secret_key=SECRET,
                    secure=False,
                )
    return  Minio(
                    os.environ["MINIO_URL"],
                    access_key=KEY,
                    secret_key=SECRET,
                    secure=False,
                )


def upload_loop():
    logger.info(os.environ["MINIO_URL"])
    minioClient = minio_client()
    try:
        minioClient.make_bucket(BUCKET, location="us-east-1")
    except MinioException:
        pass
    metlog = get_logger("upload_loop")
    while True:
        name = get_next_file()
        if name:
            try:
                start = datetime.datetime.now()
                mp4_name = f"{name[:-5]}.mp4"
                try:
                    (
                        ffmpeg
                        .input(name, format="h264", r=str(CAMERA_FRAMERATE))
                        .output(mp4_name, **{"format": "mp4", "c:v": "copy", "r": str(CAMERA_FRAMERATE)})
                        .run(quiet=True, overwrite_output=True)
                    )
                except Exception as ffmpeg_err:
                    logger.exception(ffmpeg_err)
                    logger.exception("ffmpeg_err %s", name)
                    emit(metlog, "ffmpeg_err", {"ffmpeg_err": 1})
                dur = (datetime.datetime.now() - start).total_seconds()
                logger.info('repackage took %s', dur)
                time.sleep(1)
                ts = name[11:-5]
                obj_name = (f'{DEVICE_ID}/{ts}.mp4').replace("_", "/")
                logger.info("putting %s on minio", obj_name)
                minioClient.fput_object(BUCKET, obj_name, mp4_name, content_type='video/mp4', metadata={
                                        "source": DEVICE_ID,
                                        "ts": ts,
                                        "duration": f"{PERIOD}s",
                                        })
                moved = 1
                logger.info("upload successful", extra={"metric_tag": "video_moved", "video_start_time": ts})
                try:
                    os.remove(name)
                except FileNotFoundError:
                    pass  # file disappeared?
                try:
                    os.remove(mp4_name)
                except FileNotFoundError:
                    pass  # file disappeared?
            except Exception as err:
                moved = 0
                logger.exception(err)
                logger.exception("failed to process %s", name)
            emit(metlog, "camera_move", {"ffmpeg_time_seconds": dur, "moved_to_control": moved})
        else:
            time.sleep(2)
