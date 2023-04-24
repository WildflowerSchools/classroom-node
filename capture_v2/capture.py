from datetime import datetime, timedelta
import os
import threading
import time

from libcamera import Transform
from picamera2 import MappedArray, Picamera2
from picamera2.encoders import H264Encoder, MJPEGEncoder
from picamera2.outputs import FfmpegOutput, FileOutput

import cv2

from camera_output_segmenter import CameraOutputSegmenter
from log import logger
from server import StreamingHandler, StreamingServer, StreamingOutput

from config import Settings

CLIP_DURATION = 10
CAPTURE_FRAME_RATE = 30
FRAME_RATE = 10

STREAM_ONLY = False

def next_timeslot():
    now = time.time()
    return now + (CLIP_DURATION - (now % CLIP_DURATION))

#set variables
hour = int(time.strftime('%H'))
now = time.strftime("%y_%m_%d_%H_%M")
h264_output = "test"+now+".h264"
mp4_output = "test"+now+".mp4"

#set timestamp
colour = (255, 255, 255)
origin = (0, 30)
font = cv2.FONT_HERSHEY_SIMPLEX
scale = 1
thickness = 2

def apply_timestamp(request):
    timestamp = time.strftime("%Y-%m-%d %X")
    with MappedArray(request, "main") as m:
        cv2.putText(m.array, timestamp, origin, font, scale, colour, thickness)

picam2 = Picamera2()
# picam2.pre_callback = apply_timestamp
picam2.video_configuration.transform = Transform(hflip=0, vflip=0) 
#picam2.video_configuration.controls.FrameRate = CAPTURE_FRAME_RATE
#"FrameDurationLimits": (100000, 100000)}
#"ExposureTime": 1000, "AnalogueGain": 1.0
picam2.set_controls({"FrameRate": CAPTURE_FRAME_RATE})

#picam2.video_configuration.size = (1920, 1080)
video_config = picam2.create_video_configuration(main={"size": (1296, 972), "format":"YUV420"}, lores={"size": (640, 360)})
picam2.configure(video_config)

# picam2.video_configuration.size = (1296, 972)
h264_encoder = H264Encoder(bitrate=4000000, iperiod=1)
mjpeg_encoder = MJPEGEncoder(bitrate=12000000) # Use a higher bitrate w/ MJPEG
mjpeg_encoder.framerate = CAPTURE_FRAME_RATE
mjpeg_encoder.size = video_config["lores"]["size"]
mjpeg_encoder.format = video_config["lores"]["format"]

timeslot = next_timeslot()
sleep_time = timeslot - time.time()
if sleep_time < 3:  # Ensure camera has enough time to adjust
    sleep_time += CLIP_DURATION
    timeslot += CLIP_DURATION

custom_output = CameraOutputSegmenter(
    start_datetime=datetime.fromtimestamp(timeslot),
    end_datetime=datetime.fromtimestamp(timeslot) + timedelta(seconds=600),
    clip_duration=CLIP_DURATION,
    output_dir="output",
    frame_rate=FRAME_RATE
)

monotonic_datetime_baseline = datetime.fromtimestamp(time.clock_gettime(time.CLOCK_REALTIME) - time.clock_gettime(time.CLOCK_MONOTONIC))

# address = ('', 8000)
# streaming_output = StreamingOutput()
# StreamingHandler.streaming_output = streaming_output
# server = StreamingServer(address, StreamingHandler)

settings = Settings()
server = StreamingServer(host=settings.SERVER_HOST, port=settings.SERVER_PORT)

mjpeg_encoder.output = FileOutput(server.streaming_output)

stop_threads_event = threading.Event()

def start_server(_server, stop_event: threading.Event):
    while not stop_event.is_set():
        _server.serve_forever()

def start_mjpeg_stream(stop_event: threading.Event):
    mjpeg_encoder.start()
    while not stop_event.is_set():
        request = picam2.capture_request()
        mjpeg_encoder.encode(picam2.stream_map["lores"], request)
        request.release()

server_thread = None
mjpeg_stream_thread = None
try:
    logger.info(f"Started {datetime.utcnow().strftime('%M:%S.%f')[:-3]}")

    server_thread = threading.Thread(target=start_server, args=(server, stop_threads_event,))
    server_thread.daemon = True
    server_thread.start()

    # outputs = [FileOutput(streaming_output)]
    # if not STREAM_ONLY:
    #     outputs.append(output)
    if not STREAM_ONLY:
        # picam2.start_recording(h264_encoder, custom_output)
        picam2.start_recording(MJPEGEncoder(bitrate=12000000), custom_output)
        # Wait until start_recording to fetch and store the initial "SensorTimestamp"
        capture_start_in_monotonic_seconds = picam2.capture_metadata()['SensorTimestamp'] / 1e9
        custom_output.set_camera_monotonic_start_time(capture_start_in_monotonic_seconds)
        logger.info(f"PiCam start in system monotonic seconds: {capture_start_in_monotonic_seconds}")
        logger.info(f"PiCam start in datetime: {(monotonic_datetime_baseline + timedelta(seconds=capture_start_in_monotonic_seconds)).isoformat()}")
    else:
        # picam2.start()
        picam2.start_recording(h264_encoder, "./output/out.h264")

    # Start the mjpeg stream
    mjpeg_stream_thread = threading.Thread(target=start_mjpeg_stream, args=(stop_threads_event,))
    mjpeg_stream_thread.daemon = True
    mjpeg_stream_thread.start()

    # Print some helpful details about monotonic time (i.e. how we go about getting accurate timestamps)
    logger.info(f"System's monotonic baseline in datetime: {monotonic_datetime_baseline.isoformat()}")
    # print(f"Monotonic system time (current): {time.clock_gettime(time.CLOCK_MONOTONIC)}")
    logger.info(f"Capture starting at {datetime.fromtimestamp(timeslot)}")
    
    while not custom_output.end_time_eclipsed:
        time.sleep(1)
finally:
    picam2.stop_recording()
    if custom_output.recording:
        custom_output.stop()
    server.shutdown()

    if server_thread:
        server_thread.join()
    if mjpeg_encoder:
        mjpeg_stream_thread.join()
