from datetime import datetime
from multiprocessing import Process, Queue
import os
import time
import gzip
import io
import base64

import picamera

from camnode.utils import now
from camnode.workers.honeycomb import send_data


assignment_id = "ae05f654-593a-481f-941b-ce32297b5756"


def capture_loop(control, queue):
    with picamera.PiCamera() as camera:
        camera.resolution = (1296, 730)
        camera.framerate = 15
        while True:
            name = '/out/video-{}.h264'.format(now())
            # camera.start_preview()
            camera.start_recording(name, format='h264')
            camera.wait_recording(10)
            camera.stop_recording()
            queue.put_nowait(name)
            if not control.empty():
                message = control.get()
                print("got a message in the capture loop: {}".format(message))
                if message == "STOP":
                    break


def upload_loop(control, queue):
    while True:
        print("=" * 80)
        print(" conversion loop")
        try:
            print("    {} items in the queue".format(queue.qsize()))
        except:
            print(" no idea how many are queued")
        print("=" * 80)
        if not queue.empty():
            name = queue.get()
            if name:
                send_data.apply_async(args=[assignment_id, now(), "application/json", prepare_file(name), "radio-observation.json"])
        else:
            time.sleep(3)
        if not control.empty():
            message = control.get()
            print("got a message in the convert loop: {}".format(message))
            if message == "STOP":
                print("asked to stop")
                print("still {} items in the queue".format(queue.qsize()))
                return


def prepare_file(name):
    with open(name, 'rb') as src:
        zipped = io.BytesIO()
        zipper = gzip.GzipFile("video.gz", 'wb', fileobj=zipped)
        zipper.write(src.read())
        zipped.seek(0)
        return base64.b64encode(zipped.read()).decode()


def main():
    control_1 = Queue()
    control_2 = Queue()
    queue = Queue()
    capture_process = Process(target=capture_loop, args=(control_1, queue, ))
    capture_process.start()

    ffmpeg_process = Process(target=upload_loop, args=(control_2, queue, ))
    ffmpeg_process.start()

    # time.sleep(300)
    # control_1.put("STOP")
    # time.sleep(1)
    # control_2.put("STOP")
    capture_process.join()
    ffmpeg_process.join()
