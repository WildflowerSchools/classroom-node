import datetime
from multiprocessing import Process, Queue
import os
import time

import yaml
from minio import Minio
from minio.error import (ResponseError, BucketAlreadyOwnedByYou, BucketAlreadyExists)
import picamera
import ffmpeg


with open('/boot/wildflower-config.yml', 'r') as fp:
    config = yaml.safe_load(fp.read())


ASSIGNMENT_ID = config.get("assignment-id", "unassigned")
BUCKET = os.environ.get("MINIO_BUCKET_NAME", "videos")

CAMERA_RES = (os.environ.get("CAMERA_RES_W", 1296), os.environ.get("CAMERA_RES_H", 972))
CAMERA_FRAMERATE = os.environ.get("CAMERA_FRAMERATE", 10)
INTRA_PERIOD = os.environ.get("INTRA_PERIOD", 120)
BITRATE = os.environ.get("BITRATE", 1000000)
PERIOD = os.environ.get("DURATION", 10)
CAMERA_ISO_SETTING = int(os.environ.get("CAMERA_ISO_SETTING", 400))
CAMERA_EXPOSURE_MODE = os.environ.get("CAMERA_EXPOSURE_MODE", 'sports')
CAMERA_SHUTTER_SPEED = int(os.environ.get("CAMERA_SHUTTER_SPEED", 0))


def next_timeslot(now):
    return now + (PERIOD - (now % PERIOD))


def capture_loop():
    print("starting capture")
    try:
        with picamera.PiCamera() as camera:
            camera.resolution = CAMERA_RES
            camera.framerate = CAMERA_FRAMERATE
            camera.iso = CAMERA_ISO_SETTING
            camera.exposure_mode = CAMERA_EXPOSURE_MODE
            camera.shutter_speed = CAMERA_SHUTTER_SPEED

            now = time.time()
            timeslot = next_timeslot(now)
            sleep_time = timeslot - now

            if sleep_time < 2:  # Ensure camera has enough time to adjust
                sleep_time += PERIOD
                timeslot += PERIOD
            print(f"going to sleep for a bit {sleep_time}")
            time.sleep(sleep_time)

            # camera.start_preview()
            video_start_time = datetime.datetime.fromtimestamp(timeslot)
            name = '/out/video-{:%Y_%m_%d_%H_%M-%S}.h264'.format(video_start_time)
            camera.start_recording(name, format='h264', intra_period=INTRA_PERIOD, bitrate=BITRATE)
            camera.wait_recording(PERIOD - 0.001)
            while True:
                pname = name
                timeslot += PERIOD
                video_start_time = datetime.datetime.fromtimestamp(timeslot)
                name = '/out/video-{:%Y_%m_%d_%H_%M-%S}.h264'.format(video_start_time)
                camera.split_recording(name, format='h264', intra_period=INTRA_PERIOD, bitrate=BITRATE)
                delay = timeslot + PERIOD - time.time()
                print("waiting %s" % delay)
                camera.wait_recording(delay)
    except Exception as e:
        print(e)



def get_next_file():
    for item in os.listdir('/out'):
        if item.endswith(".h264"):
            fname = f'/out/{item}'
            st = os.stat(fname)
            if st.st_mtime > 11:
                return fname
    return None


def upload_loop(minioClient):
    minioClient = Minio(os.environ.get("MINIO_URL", "minio-service.classroom.svc.cluster.local:9000"),
                        access_key=os.environ.get("MINIO_KEY", "wildflower-classroom"),
                        secret_key=os.environ.get("MINIO_SECRET"),
                        secure=False)

    try:
        minioClient.make_bucket(BUCKET, location="us-east-1")
    except BucketAlreadyOwnedByYou as err:
        pass
    except BucketAlreadyExists as err:
        pass
    except ResponseError as err:
        raise
    while True:
        print("=" * 80)
        print(" upload loop")
        print("=" * 80)
        name = get_next_file()
        if name:
            try:
                start = datetime.datetime.now()
                mp4_name = "%s.mp4" % name[:-5]
                (
                    ffmpeg
                    .input(name, format="h264", r=str(CAMERA_FRAMERATE))
                    .output(mp4_name, **{"format": "mp4", "c:v": "copy", "r": str(CAMERA_FRAMERATE)})
                    .run(quiet=False)
                )
                print('repackage took %s' % (datetime.datetime.now() - start).total_seconds())
                time.sleep(1)
                ts = name[11:-5]
                obj_name = ('%s/%s.mp4' % (ASSIGNMENT_ID, ts)).replace("_", "/")
                print("putting %s on minio" % obj_name)
                minioClient.fput_object(BUCKET, obj_name, mp4_name, content_type='video/mp4', metadata={
                                        "source": ASSIGNMENT_ID,
                                        "ts": ts,
                                        "duration": "%ss" % PERIOD,
                                        })
                os.remove(name)
                os.remove(mp4_name)
            except ResponseError as err:
                print(err)
                print("failed to process %s" % name)
    else:
        time.sleep(2)


