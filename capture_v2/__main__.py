from datetime import datetime
from functools import partial
import sys

from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput

from .camera_controller import CameraController
from .camera_output_segmenter import CameraOutputSegmenter
from .config import Settings
from .log import logger
from .scheduler import Scheduler
from .server import StreamingServer
from .uploader import MinioVideoUploader
from . import util


def main():
    settings = Settings()

    if settings.CLASSROOM_ENVIRONMENT_ID is None:
        logger.error("CLASSROOM_ENVIRONMENT_ID is required")
        return

    server, camera_controller, uploader = None, None, None
    try:
        server = StreamingServer(host=settings.SERVER_HOST, port=settings.SERVER_PORT)

        camera_controller = CameraController(
            main_config={"size": (1296, 972), "format": "YUV420"},
            lores_config={"size": (640, 360), "format": "YUV420"},
            capture_frame_rate=settings.CAMERA_CAPTURE_FRAME_RATE,
            hflip=settings.CAMERA_H_FLIP,
            vflip=settings.CAMERA_V_FLIP,
        )

        mjpeg_lo_res_encoder = MJPEGEncoder(bitrate=12000000)
        mjpeg_lo_res_encoder.output = FileOutput(server.streaming_output)

        custom_output = CameraOutputSegmenter(
            # start_datetime=datetime.fromtimestamp(util.next_timeslot()),
            clip_duration=settings.VIDEO_CLIP_DURATION,
            staging_dir=settings.VIDEO_CLIP_STAGING_DIR,
            output_dir=settings.VIDEO_CLIP_OUTPUT_DIR,
            frame_rate=settings.VIDEO_CLIP_FRAME_RATE,
        )
        mjpeg_main_res_encoder = MJPEGEncoder(bitrate=12000000)
        mjpeg_main_res_encoder.output = custom_output

        camera_controller.add_encoder(
            encoder=mjpeg_lo_res_encoder,
            name="LoRes MJPEG Encoder - For Streaming HTTP Server",
            stream_type="lores",
        )
        camera_controller.start()

        encoder_capture_loop_id = camera_controller.add_encoder(
            encoder=mjpeg_main_res_encoder,
            name="HiRes MJPEG Encoder - For Capture Loop",
            stream_type="main",
        )

        if settings.MINIO_ENABLE:
            uploader = MinioVideoUploader(
                output_dir=settings.VIDEO_CLIP_OUTPUT_DIR,
                remove_video_after_upload=True,
            )
            uploader.start()

        server.start(background=True)

        capture_scheduler = Scheduler(environment_id=settings.CLASSROOM_ENVIRONMENT_ID)
        capture_scheduler.add_class_hours_tasks(
            name="capture",
            during_class_hours_callback=camera_controller.start_encoder,
            outside_class_hours_callback=camera_controller.stop_encoder,
            during_class_hours_kwargs={"encoder_id": encoder_capture_loop_id},
            outside_class_hours_kwargs={"encoder_id": encoder_capture_loop_id},
        )
        capture_scheduler.start()
    finally:
        if server is not None:
            server.stop()
        if uploader is not None:
            uploader.stop()
        if camera_controller is not None:
            camera_controller.stop()


if __name__ == "__main__":
    sys.exit(main())
