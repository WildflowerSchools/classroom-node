import sys
import time

from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput

from .camera.camera_controller import CameraController
from .camera.camera_output_segmenter import CameraOutputSegmenter
from .config import Settings
from .log import logger
from .scheduler.scheduler import Scheduler
from .server.server import StreamingServer
from .uploader.uploader import MinioVideoUploader


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

        # Create/add our first encoder for the HTTP Stream
        mjpeg_lo_res_encoder = MJPEGEncoder(bitrate=18000000)
        mjpeg_lo_res_encoder.output = FileOutput(server.streaming_output)
        camera_controller.add_encoder(
            encoder=mjpeg_lo_res_encoder,
            name="LoRes MJPEG Encoder - For Streaming HTTP Server",
            stream_type="lores",
        )
        # We start the camera with knowledge of the Lores encoder for the HTTP streaming only
        # Later, we add the CameraOutputSegmenter encoder and leave it up to the Scheduler to turn on/off
        camera_controller.start()

        # Create/add our fancy CameraOutputSegmenter encoder for turning the stream into video files
        custom_output = CameraOutputSegmenter(
            clip_duration=settings.VIDEO_CLIP_DURATION,
            staging_dir=settings.VIDEO_CLIP_STAGING_DIR,
            output_dir=settings.VIDEO_CLIP_OUTPUT_DIR,
            frame_rate=settings.VIDEO_CLIP_FRAME_RATE,
            finalize_video_in_background=settings.FINALIZE_VIDEO_IN_BACKGROUND,
        )
        mjpeg_main_res_encoder = MJPEGEncoder(bitrate=18000000)
        mjpeg_main_res_encoder.output = custom_output
        encoder_capture_loop_id = camera_controller.add_encoder(
            encoder=mjpeg_main_res_encoder,
            name="HiRes MJPEG Encoder - For Capture Loop",
            stream_type="main",
        )

        # Start Minio if the MINIO_ENABLE env var was set
        if settings.MINIO_ENABLE:
            uploader = MinioVideoUploader(
                output_dir=settings.VIDEO_CLIP_OUTPUT_DIR,
                remove_video_after_upload=True,
            )
            uploader.start()

        server.start(background=True)

        # Start the "Scheduler"
        # Scheduler is responsible for starting/stopping the CameraOutputSegmenter encoder which
        # converts camera output -> video files.
        # It uses the classroom environment ID to fetch a classroms start/stop time
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
