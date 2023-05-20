import copy
import random
import string
import threading
from typing import Optional, Union

from libcamera import Transform, controls
from picamera2 import Picamera2
from picamera2.encoders import Encoder, Quality
from picamera2.outputs import Output

from capture_v2.log import logger


class _EncoderWrapper:
    def __init__(self, encoder: Encoder, name: str = "", stream_type: str = "main"):
        self.encoder: Encoder = encoder
        self.name: str = name
        self.stream_type: str = stream_type


class EncoderError(Exception):
    pass


class CameraController:
    def __init__(
        self,
        main_config: dict,
        lores_config: dict = None,
        capture_frame_rate: int = 30,
        hflip: bool = False,
        vflip: bool = False,
    ):
        self.picam2 = Picamera2()
        self.picam2.options["quality"] = 95  # Highest quality available
        self.picam2.options["compress_level"] = 0  # No compression

        _hflip = 1 if hflip else 0
        _vflip = 1 if vflip else 0

        self.picam2.configure(
            self.picam2.create_video_configuration(
                main=main_config,
                lores=lores_config,
                transform=Transform(hflip=_hflip, vflip=_vflip),
            )
        )
        self.picam2.set_controls(
            {
                "FrameRate": capture_frame_rate,
                "NoiseReductionMode": controls.draft.NoiseReductionModeEnum.HighQuality,
                "AeExposureMode": controls.AeExposureModeEnum.Long,
            }
        )

        self.encoders: dict[str, _EncoderWrapper] = {}
        self.capture_start_in_monotonic_seconds: int = None

        self.capture_reading_thread: threading.Thread = None
        self.stop_event: threading.Event = threading.Event()

    def random_id(self):
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=10))

    def start_camera(self):
        logger.info("Starting camera system...")
        self.picam2.start()

    def stop_camera(self):
        self.picam2.stop()

    def stop(self):
        for id, e in list(self.encoders.items()):
            self.stop_encoder(encoder_id=id)

        self.stop_event.set()
        if self.capture_reading_thread.is_alive():
            self.capture_reading_thread.join()

        logger.info(f"Stopped capture reading thread")

        self.stop_event.clear()
        self.capture_reading_thread = None

        self.stop_camera()

    def start(self):
        self.start_camera()

        self.capture_reading_thread = threading.Thread(
            target=self._start_capture_read,
            daemon=False,
        )
        self.capture_reading_thread.start()

        for id, e in list(self.encoders.items()):
            self.start_encoder(encoder_id=id)

    def _start_capture_read(self):
        while not self.stop_event.is_set():
            request = self.picam2.capture_request()

            for _, e in list(self.encoders.items()):
                if e.encoder._running:
                    stream = self.picam2.stream_map[e.stream_type]

                    if e.encoder.firsttimestamp is None:
                        fb = request.request.buffers[stream]
                        encoder_start_in_monotonic_seconds = int(fb.metadata.timestamp / 1e9)
                        
                        if hasattr(
                            e.encoder.output, "set_encoder_monotonic_start_time"
                        ):
                            e.encoder.output.set_encoder_monotonic_start_time(
                                encoder_start_in_monotonic_seconds
                            )
                        
                        logger.info(
                            f"Started encoder '{e.name}' at monotonic time (in seconds) '{encoder_start_in_monotonic_seconds}'"
                        )

                    e.encoder.encode(stream, request)
            request.release()

    def add_encoder(self, encoder: Encoder, name="", stream_type="main") -> str:
        id = self.random_id()
        self.encoders[id] = _EncoderWrapper(
            encoder=encoder, name=name, stream_type=stream_type
        )
        return id

    def get_wrapped_encoder(
        self, encoder_id: str = None, encoder: Encoder = None
    ) -> tuple[Optional[str], Optional[_EncoderWrapper]]:
        selected_encoder_id = None
        selected_encoder_wrapper = None
        if encoder_id is not None:
            if encoder_id in self.encoders:
                selected_encoder_id = encoder_id
                selected_encoder_wrapper = self.encoders[encoder_id]
        elif encoder is not None:
            for id, wrapped_encoder in list(self.encoders.items()):
                if wrapped_encoder.encoder == encoder:
                    selected_encoder_id = id
                    selected_encoder_wrapper = wrapped_encoder

        return selected_encoder_id, selected_encoder_wrapper

    def remove_encoder(self, encoder_id: str = None, encoder: Encoder = None):
        selected_encoder_id, selected_encoder_wrapper = self.get_wrapped_encoder(
            encoder_id=encoder_id, encoder=encoder
        )
        if selected_encoder_id is None or selected_encoder_wrapper is None:
            return

        self.stop_encoder(
            encoder_id=encoder_id, encoder=selected_encoder_wrapper.encoder
        )
        self.encoders.pop(selected_encoder_id)

    def set_encoder_output(
        self,
        output: Union[Output, list[Output]],
        encoder_id: str = None,
        encoder: Encoder = None,
    ):
        selected_encoder_id, selected_encoder_wrapper = self.get_wrapped_encoder(
            encoder_id=encoder_id, encoder=encoder
        )
        if selected_encoder_id is None or selected_encoder_wrapper is None:
            return

        selected_encoder_wrapper.encoder.output = output

    def start_encoder(self, encoder_id: str = None, encoder: Encoder = None):
        selected_encoder_id, selected_encoder_wrapper = self.get_wrapped_encoder(
            encoder_id=encoder_id, encoder=encoder
        )
        if selected_encoder_id is None or selected_encoder_wrapper is None:
            return

        if selected_encoder_wrapper.encoder is None:
            self.stop_encoder(encoder_id=encoder_id, encoder=encoder)
            err = f"Unable to start encoder '{selected_encoder_wrapper.name}', the encoder object itself is set to None"
            logger.error(err)
            raise EncoderError(err)

        if selected_encoder_wrapper.encoder._running:
            logger.warning(
                f"Encoder ID '{selected_encoder_wrapper.name}' is already running"
            )
            return

        streams = self.picam2.camera_configuration()
        (
            selected_encoder_wrapper.encoder.width,
            selected_encoder_wrapper.encoder.height,
        ) = streams[selected_encoder_wrapper.stream_type]["size"]
        selected_encoder_wrapper.encoder.format = streams[
            selected_encoder_wrapper.stream_type
        ]["format"]
        selected_encoder_wrapper.encoder.stride = streams[
            selected_encoder_wrapper.stream_type
        ]["stride"]
        min_frame_duration = self.picam2.camera_ctrl_info["FrameDurationLimits"][1].min
        min_frame_duration = max(min_frame_duration, 33333)
        selected_encoder_wrapper.encoder.framerate = 1000000 / min_frame_duration
        selected_encoder_wrapper.encoder._setup(
            Quality.HIGH
        )  # default to high bitrate if a bitrate wasn't supplied when initializing the encoder

        selected_encoder_wrapper.encoder.start()

    def stop_encoder(self, encoder_id: str = None, encoder: Encoder = None):
        selected_encoder_id, selected_encoder_wrapper = self.get_wrapped_encoder(
            encoder_id=encoder_id, encoder=encoder
        )
        if selected_encoder_id is None or selected_encoder_wrapper is None:
            return

        logger.info(f"Stopping encoding thread '{selected_encoder_wrapper.name}'...")
        if selected_encoder_wrapper.encoder._running:
            selected_encoder_wrapper.encoder.stop()
        logger.info(f"Stopped encoding thread '{selected_encoder_wrapper.name}'")
