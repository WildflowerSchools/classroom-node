
from multiprocessing import Process, Queue
import os
import time

from minio import Minio
from minio.error import (ResponseError, BucketAlreadyOwnedByYou,
                         BucketAlreadyExists)
import picamera

from camnode.utils import now


ASSIGNMENT_ID = os.environ.get("WF_ASSIGNMENT_ID")
BUCKET = os.environ.get("MINIO_BUCKET_NAME")

CAMERA_RES = (os.environ.get("CAMERA_RES_W", 1296), os.environ.get("CAMERA_RES_H", 730))
CAMERA_FRAMERATE = os.environ.get("CAMERA_FRAMERATE", 15)
INTRA_PERIOD = os.environ.get("INTRA_PERIOD", 100)
BITRATE = os.environ.get("BITRATE", 1000000)
PERIOD = os.environ.get("DURATION", 10)


def capture_loop(control, queue):
    with picamera.PiCamera() as camera:
        camera.resolution = CAMERA_RES
        camera.framerate = CAMERA_FRAMERATE

        name = '/out/video-{}.h264'.format(now())
        # camera.start_preview()
        camera.start_recording(name, format='h264', intra_period=INTRA_PERIOD, bitrate=BITRATE)
        camera.wait_recording(PERIOD)
        queue.put_nowait(name)
        while True:
            name = '/out/video-{}.h264'.format(now())
            camera.split_recording(name, format='h264', intra_period=INTRA_PERIOD, bitrate=BITRATE)
            camera.wait_recording(PERIOD)
            queue.put_nowait(name)
            if not control.empty():
                message = control.get()
                print("got a message in the capture loop: {}".format(message))
                if message == "STOP":
                    camera.stop_recording()
                    break


def upload_loop(control, queue, minioClient):
    while True:
        print("=" * 80)
        print(" upload loop")
        try:
            print("    {} items in the queue".format(queue.qsize()))
        except Exception:
            print(" no idea how many are queued")
        print("=" * 80)
        if not queue.empty():
            name = queue.get()
            if name:
                try:
                    ts = name[11:-5]
                    minioClient.fput_object(BUCKET, '/%s/%s.h264' % (ASSIGNMENT_ID, ts.replace('-', '/').replace('T', '/')), name, content_type='video/h264', metadata={
                                            "source": ASSIGNMENT_ID,
                                            "ts": ts,
                                            "duration": "%ss" % PERIOD,
                                            })
                    os.remove(name)
                except ResponseError as err:
                    print(err)
        else:
            time.sleep(2)
        if not control.empty():
            message = control.get()
            print("got a message in the upload loop: {}".format(message))
            if message == "STOP":
                print("asked to stop")
                print("still {} items in the queue".format(queue.qsize()))
                return

def main():
    minioClient = Minio(os.environ.get("MINIO_URL"),
                        access_key=os.environ.get("MINIO_KEY"),
                        secret_key=os.environ.get("MINIO_SECRET"),
                        secure=True)

    try:
        minioClient.make_bucket(BUCKET, location="us-east-1")
    except BucketAlreadyOwnedByYou as err:
        pass
    except BucketAlreadyExists as err:
        pass
    except ResponseError as err:
        raise
    control_1 = Queue()
    control_2 = Queue()
    queue = Queue()
    capture_process = Process(target=capture_loop, args=(control_1, queue, ))
    capture_process.start()

    ffmpeg_process = Process(target=upload_loop, args=(control_2, queue, minioClient, ))
    ffmpeg_process.start()

    capture_process.join()
    ffmpeg_process.join()
