from datetime import datetime
import sys

from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput

from .camera_controller import CameraController
from .camera_output_segmenter import CameraOutputSegmenter
from .config import Settings
from .server import StreamingServer
from .uploader import MinioVideoUploader
from . import util


def main():
    settings = Settings()

    server, camera_controller, uploader = None, None, None
    try:
        server = StreamingServer(host=settings.SERVER_HOST, port=settings.SERVER_PORT)

        camera_controller = CameraController(
            main_config={"size": (1296, 972), "format": "YUV420"},
            lores_config={"size": (640, 360), "format": "YUV420"},
            capture_frame_rate=settings.CAMERA_CAPTURE_FRAME_RATE,
        )

        mjpeg_lo_res_encoder = MJPEGEncoder(bitrate=12000000)
        mjpeg_lo_res_encoder.output = FileOutput(server.streaming_output)

        custom_output = CameraOutputSegmenter(
            start_datetime=datetime.fromtimestamp(util.next_timeslot()),
            clip_duration=settings.VIDEO_CLIP_DURATION,
            staging_dir=settings.VIDEO_CLIP_STAGING_DIR,
            output_dir=settings.VIDEO_CLIP_OUTPUT_DIR,
            frame_rate=settings.VIDEO_CLIP_FRAME_RATE,
        )
        mjpeg_main_res_encoder = MJPEGEncoder(bitrate=12000000)
        mjpeg_main_res_encoder.output = custom_output

        camera_controller.add_encoder(
            encoder=mjpeg_main_res_encoder,
            name="HiRes MJPEG Encoder - For Capture Loop",
            stream_type="main",
        )
        camera_controller.add_encoder(
            encoder=mjpeg_lo_res_encoder,
            name="LoRes MJPEG Encoder - For Streaming HTTP Server",
            stream_type="lores",
        )
        camera_controller.start()

        if settings.MINIO_ENABLE:
            uploader = MinioVideoUploader(
                output_dir=settings.VIDEO_CLIP_OUTPUT_DIR,
                remove_video_after_upload=True,
            )
            uploader.start()

        server.start()
    finally:
        if server is not None:
            server.stop()
        if uploader is not None:
            uploader.stop()
        if camera_controller is not None:
            camera_controller.stop()


if __name__ == "__main__":
    sys.exit(main())
