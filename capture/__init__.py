import datetime
import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)-9s %(asctime)s [%(filename)-15s:%(funcName)-12s] %(message)s')
from multiprocessing import Process, Queue
import os
import time

import yaml
from minio import Minio
from minio.error import MinioException
try:
    import picamera
except ImportError:
    logging.warning("picamera not available")

import ffmpeg


logging.basicConfig(level=logging.DEBUG, format='%(levelname)-9s %(asctime)s [%(filename)-15s:%(funcName)-12s] %(message)s')


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


def next_timeslot(now):
    return now + (PERIOD - (now % PERIOD))


def capture_loop():
    logging.info("starting capture")
    try:
        with picamera.PiCamera() as camera:
            camera.resolution = CAMERA_RES
            camera.framerate = CAMERA_FRAMERATE
            camera.iso = CAMERA_ISO_SETTING
            camera.exposure_mode = CAMERA_EXPOSURE_MODE
            camera.shutter_speed = CAMERA_SHUTTER_SPEED
            logging.info("period is %s", PERIOD)
            camera.hflip = CAMERA_H_FLIP == "yes"
            camera.vflip = CAMERA_V_FLIP == "yes"

            now = time.time()
            timeslot = next_timeslot(now)
            sleep_time = timeslot - now

            if sleep_time < 2:  # Ensure camera has enough time to adjust
                sleep_time += PERIOD
                timeslot += PERIOD
            logging.info("going to sleep for a bit %s", sleep_time)
            time.sleep(sleep_time)

            # camera.start_preview()
            video_start_time = datetime.datetime.fromtimestamp(timeslot)
            name = f'/out/video-{video_start_time:%Y_%m_%d_%H_%M-%S}.h264'
            camera.start_recording(name, format='h264', intra_period=INTRA_PERIOD, bitrate=BITRATE)
            camera.wait_recording(PERIOD - 0.001)
            while True:
                timeslot += PERIOD
                video_start_time = datetime.datetime.fromtimestamp(timeslot)
                name = f'/out/video-{video_start_time:%Y_%m_%d_%H_%M-%S}.h264'
                camera.split_recording(name, format='h264', intra_period=INTRA_PERIOD, bitrate=BITRATE)
                delay = timeslot + PERIOD - time.time()
                logging.info("waiting %s", delay)
                camera.wait_recording(delay)
    except Exception as e:
        logging.info(e)



def get_next_file():
    for item in os.listdir('/out'):
        if item.endswith(".h264"):
            fname = f'/out/{item}'
            st = os.stat(fname)
            if (time.time() - st.st_mtime) > 11 and st.st_size > 800000:
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
    logging.info(os.environ["MINIO_URL"])
    minioClient = minio_client()
    try:
        minioClient.make_bucket(BUCKET, location="us-east-1")
    except MinioException:
        pass
    while True:
        name = get_next_file()
        if name:
            try:
                start = datetime.datetime.now()
                mp4_name = f"{name[:-5]}.mp4"
                (
                    ffmpeg
                    .input(name, format="h264", r=str(CAMERA_FRAMERATE))
                    .output(mp4_name, **{"format": "mp4", "c:v": "copy", "r": str(CAMERA_FRAMERATE)})
                    .run(quiet=False, overwrite_output=True)
                )
                logging.info('repackage took %s', (datetime.datetime.now() - start).total_seconds())
                time.sleep(1)
                ts = name[11:-5]
                obj_name = (f'{DEVICE_ID}/{ts}.mp4').replace("_", "/")
                logging.info("putting %s on minio", obj_name)
                minioClient.fput_object(BUCKET, obj_name, mp4_name, content_type='video/mp4', metadata={
                                        "source": DEVICE_ID,
                                        "ts": ts,
                                        "duration": f"{PERIOD}s",
                                        })
                os.remove(name)
                os.remove(mp4_name)
            except MinioException as err:
                logging.info(err)
                logging.info("failed to process %s", name)
        else:
            time.sleep(2)
