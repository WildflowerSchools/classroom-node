from datetime import datetime
from multiprocessing import Process, Queue
import os
import time

import ffmpeg
import picamera


def capture_loop(control, queue):
    with picamera.PiCamera() as camera:
        camera.resolution = (1296, 730)
        camera.framerate = 15
        for i in range(10):
            name = 'video-{}.h264'.format(i)
            camera.start_preview()
            camera.start_recording(name, format='h264')
            camera.wait_recording(10)
            camera.stop_recording()
            queue.put_nowait(name)
            if not control.empty():
                message = control.get()
                print("got a message in the capture loop: {}".format(message))
                if message == "STOP":
                    break


def ffmpeg_loop(control, queue):
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
                (
                ffmpeg
                    .input(name)
                    .filter('fps', fps=5, round='up')
                    .output("output/{}-%04d.jpg".format(name[:-5]))
                    .run()
                )
                os.rename(name, "output/{}".format(name))
        else:
            time.sleep(1)
        if not control.empty():
            message = control.get()
            print("got a message in the convert loop: {}".format(message))
            if message == "STOP":
                print("asked to stop")
                print("still {} items in the queue".format(queue.qsize()))
                return


if __name__ == '__main__':
    control_1 = Queue()
    control_2 = Queue()
    queue = Queue()
    capture_process = Process(target=capture_loop, args=(control_1, queue, ))
    capture_process.start()

    ffmpeg_process = Process(target=ffmpeg_loop, args=(control_2, queue, ))
    ffmpeg_process.start()

    time.sleep(300)
    control_1.put("STOP")
    time.sleep(1)
    control_2.put("STOP")
    capture_process.join()
    ffmpeg_process.join()
