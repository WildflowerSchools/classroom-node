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
INTRA_PERIOD = os.environ.get("INTRA_PERIOD", 20)
BITRATE = os.environ.get("BITRATE", 1000000)
PERIOD = os.environ.get("DURATION", 10)


def next_timeslot(now):
    return now + (PERIOD - (now % PERIOD))


def capture_loop(control, queue):
    with picamera.PiCamera() as camera:
        camera.resolution = CAMERA_RES
        camera.framerate = CAMERA_FRAMERATE

        now = time.time()
        timeslot = next_timeslot(now)
        sleep_time = timeslot - now

        if sleep_time < 2:  # Ensure camera has enough time to adjust
            sleep_time += PERIOD
            timeslot += PERIOD

        time.sleep(sleep_time)

        # camera.start_preview()
        video_start_time = datetime.datetime.fromtimestamp(timeslot)
        name = '/out/video-{:%Y_%m_%d_%H_%M-%S}.h264'.format(video_start_time)
        camera.start_recording(name, format='h264', intra_period=INTRA_PERIOD, bitrate=BITRATE)
        camera.wait_recording(PERIOD - 0.1)
        while True:
            camera.split_recording(name, format='h264', intra_period=INTRA_PERIOD, bitrate=BITRATE)
            queue.put_nowait(name)
            timeslot += PERIOD
            video_start_time = datetime.datetime.fromtimestamp(timeslot)
            name = '/out/video-{:%Y_%m_%d_%H_%M-%S}.h264'.format(video_start_time)
            delay = timeslot + PERIOD - time.time()
            camera.wait_recording(delay - 0.1)
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
                    start = datetime.datetime.now()
                    mp4_name = "%s.mp4" % name[:-5]
                    (
                        ffmpeg
                        .input(name, format="h264")
                        .output(mp4_name, format="mp4", c="copy", r="10")
                        .run(quiet=True)
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
                except ResponseError as err:
                    print(err)
                    print("failed to process %s" % name)
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
    minioClient = Minio(os.environ.get("MINIO_URL", "inio-service.classroom.svc.cluster.local:9000"),
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
    control_1 = Queue()
    control_2 = Queue()
    queue = Queue()
    capture_process = Process(target=capture_loop, args=(control_1, queue, ))
    capture_process.start()

    ffmpeg_process = Process(target=upload_loop, args=(control_2, queue, minioClient, ))
    ffmpeg_process.start()

    capture_process.join()
    ffmpeg_process.join()
