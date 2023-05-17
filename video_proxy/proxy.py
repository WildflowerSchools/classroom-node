from dataclasses import dataclass
import io
import threading

import av


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


@dataclass
class CameraStream:
    """Class for keeping track of an item in inventory."""
    device_name: str
    device_id: str
    device_ip: str = 0
    streaming_port: int = 8000
    streaming_output: StreamingOutput = StreamingOutput()
    thread: threading.Thread = None

    @property
    def url(self) -> str:
        return f"http://{self.device_ip}:{self.streaming_port}/stream.mjpg"

    def _start_thread(self):
        container = av.open(self.url)

        for packet in container.demux():
            for frame in packet.decode():
                img = frame.to_image()
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                img_byte_arr.seek(0)
                self.streaming_output.write(img_byte_arr.getvalue())

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self._start_thread, daemon=True,)
            self.thread.start()

    def read(self):
        self.start()

        with self.streaming_output.condition:
            self.streaming_output.condition.wait()
            yield self.streaming_output.frame


class Proxy:
    def __init__(self):
        self.registered: list[CameraStream] = []

    def add_stream(self, stream: CameraStream):
        self.registered.append(stream)

    def read_stream(self, device_id):
        stream = next(filter(lambda r: r.device_id == device_id, self.registered), None)
        if stream:
            return stream.read()

    def remove_stream(self):
        pass

