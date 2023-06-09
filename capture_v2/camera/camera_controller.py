import random
import string
import threading
from typing import List, Optional, Union

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
        self.paused: bool = False
        self.initialized: bool = False

    @property
    def outputs(self) -> List[Output]:
        if type(self.encoder.output) is list:
            encoder_outputs = self.encoder.output
        else:
            encoder_outputs = [self.encoder.output]

        return encoder_outputs

    def has_any_recording_outputs(self) -> bool:
        return any(map(lambda o: o.recording, self.outputs))


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

        self.encoders_lock: threading.Lock = threading.Lock()
        self.encoders: dict[str, _EncoderWrapper] = {}
        self.capture_start_in_monotonic_seconds: int = None

        self.capture_reading_thread: threading.Thread = None
        self.stop_event: threading.Event = threading.Event()

    def random_id(self):
        return "".join(random.choices(string.ascii_lowercase + string.digits, k=10))

    def start_camera(self):
        logger.info("Starting picamera2 camera system...")
        self.picam2.start()
        logger.info("Started picamera2 camera system")

    def stop_camera(self):
        logger.info("Stopping picamera2 camera system...")
        self.picam2.stop()
        logger.info("Stopped picamera2 camera system")

    def stop(self):
        logger.info("Stopping camera controller...")
        with self.encoders_lock:
            for id, e in list(self.encoders.items()):
                self.stop_encoder(encoder_id=id)

        self.stop_event.set()
        if self.capture_reading_thread and self.capture_reading_thread.is_alive():
            self.capture_reading_thread.join()

        logger.info(f"Stopped capture reading thread")

        self.stop_event.clear()
        self.capture_reading_thread = None

        self.stop_camera()
        logger.info("Stopped camera controller")

    def start(self):
        logger.info("Starting camera controller...")
        self.start_camera()

        self.capture_reading_thread = threading.Thread(
            target=self._start_capture_read,
            name="CaptureReadLoop",
            daemon=False,
        )
        self.capture_reading_thread.start()
        logger.info(f"Started capture reading thread")

        with self.encoders_lock:
            for id, e in list(self.encoders.items()):
                if not e.paused:
                    self.start_encoder(encoder_id=id)
        logger.info("Started camera controller")

    def _start_capture_read(self):
        ii = 0

        logger.info("Starting the capture read loop...")

        while not self.stop_event.is_set():
            ii += 1

            if ii == 1:
                logger.info("Started the capture read loop")

            # with self.encoders_lock:
            # Every 1000 frames we log details about the encoders and their status
            if ii == 1 or ii % 1000 == 0:
                encoder_details = []
                for e in list(self.encoders.values()):
                    encoder_name = e.name
                    encoder_running = e.encoder._running

                    encoder_output_status = []
                    for o in e.outputs:
                        encoder_output_status.append(
                            f"Handler Class: '{type(o).__name__}' - Handler Recording: '{o.recording}'"
                        )

                    encoder_details.append(
                        f"Encoder Name: '{encoder_name}' Encoder Running: '{encoder_running}' Encoder Output Handler(s): {encoder_output_status}"
                    )

                encoder_details_with_newlines = "\n".join(encoder_details)
                logger.info(
                    f"Capture loop status update: captured {ii} frames, Encoders: \n{encoder_details_with_newlines}"
                )

            request = None
            try:
                request = self.picam2.capture_request()

                for _, e in list(self.encoders.items()):
                    if not e.encoder._running or e.paused:
                        continue

                    stream = self.picam2.stream_map[e.stream_type]

                    if e.encoder.firsttimestamp is None:
                        fb = request.request.buffers[stream]
                        encoder_start_in_monotonic_seconds = (
                            fb.metadata.timestamp / 1e9
                        )

                        if hasattr(
                            e.encoder.output, "set_encoder_monotonic_start_time"
                        ):
                            e.encoder.output.set_encoder_monotonic_start_time(
                                encoder_start_in_monotonic_seconds
                            )

                        logger.info(
                            f"Started encoder '{e.name}' at monotonic time (in seconds) '{encoder_start_in_monotonic_seconds}'"
                        )

                    if e.has_any_recording_outputs():
                        e.encoder.encode(stream, request)
            finally:
                if request is not None:
                    request.release()

        logger.info("Stopped the capture read loop")

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

    def add_encoder(self, encoder: Encoder, name="", stream_type="main") -> str:
        with self.encoders_lock:
            selected_encoder_id, selected_encoder_wrapper = self.get_wrapped_encoder(
                encoder_id=None, encoder=encoder
            )
            if selected_encoder_id is not None or selected_encoder_wrapper is not None:
                logger.warning(
                    "Not adding Encoder, an EncoderWrapper already exists for this encoder"
                )
                return selected_encoder_id

            id = self.random_id()
            self.encoders[id] = _EncoderWrapper(
                encoder=encoder, name=name, stream_type=stream_type
            )
            return id

    def remove_encoder(self, encoder_id: str = None, encoder: Encoder = None):
        with self.encoders_lock:
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
        with self.encoders_lock:
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

        logger.info(f"Starting encoder '{selected_encoder_wrapper.name}'...")

        if selected_encoder_wrapper.encoder is None:
            self.stop_encoder(encoder_id=encoder_id, encoder=encoder)
            err = f"Unable to start encoder '{selected_encoder_wrapper.name}', the encoder object itself is set to None"
            logger.error(err)
            raise EncoderError(err)

        if selected_encoder_wrapper.encoder._running:
            selected_encoder_wrapper.paused = False
            logger.warning(
                f"Encoder '{selected_encoder_wrapper.name}' is already running"
            )
            return

        if not selected_encoder_wrapper.initialized:
            stream_configuration = self.picam2.camera_configuration()[
                selected_encoder_wrapper.stream_type
            ]
            (
                selected_encoder_wrapper.encoder.width,
                selected_encoder_wrapper.encoder.height,
            ) = stream_configuration["size"]
            selected_encoder_wrapper.encoder.format = stream_configuration["format"]
            selected_encoder_wrapper.encoder.stride = stream_configuration["stride"]
            min_frame_duration = self.picam2.camera_ctrl_info["FrameDurationLimits"][1].min
            min_frame_duration = max(min_frame_duration, 33333)
            selected_encoder_wrapper.encoder.framerate = 1000000 / min_frame_duration
            selected_encoder_wrapper.encoder._setup(
                Quality.HIGH
            )  # default to high bitrate if a bitrate wasn't supplied when initializing the encoder
            
            selected_encoder_wrapper.initialized = True

        selected_encoder_wrapper.paused = False
        selected_encoder_wrapper.encoder.start()
        logger.info(f"Started encoder '{selected_encoder_wrapper.name}'")

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

    def pause_encoder(self, encoder_id: str = None, encoder: Encoder = None):
        """
        A paused encoder won't start back up if the camera system is rebooted. The only way to
        get a paused encoder to start is to explicity call start_encoder
        """
        selected_encoder_id, selected_encoder_wrapper = self.get_wrapped_encoder(
            encoder_id=encoder_id, encoder=encoder
        )
        if selected_encoder_id is None or selected_encoder_wrapper is None:
            return

        self.stop_encoder(encoder_id=encoder_id, encoder=encoder)

        selected_encoder_wrapper.paused = True

    def start_encoder_outputs(self, encoder_id: str = None, encoder: Encoder = None):
        selected_encoder_id, selected_encoder_wrapper = self.get_wrapped_encoder(
            encoder_id=encoder_id, encoder=encoder
        )
        if selected_encoder_id is None or selected_encoder_wrapper is None:
            return

        logger.info(f"Starting '{selected_encoder_wrapper.name}' outputters...")
        with self.encoders_lock:
            for o in selected_encoder_wrapper.outputs:
                o.start()
        logger.info(f"Started '{selected_encoder_wrapper.name}' outputters")

    def stop_encoder_outputs(self, encoder_id: str = None, encoder: Encoder = None):
        selected_encoder_id, selected_encoder_wrapper = self.get_wrapped_encoder(
            encoder_id=encoder_id, encoder=encoder
        )
        if selected_encoder_id is None or selected_encoder_wrapper is None:
            return

        logger.info(f"Stopping '{selected_encoder_wrapper.name}' outputters...")
        with self.encoders_lock:
            for o in selected_encoder_wrapper.outputs:
                o.stop()
        logger.info(f"Stopped '{selected_encoder_wrapper.name}' outputters")
