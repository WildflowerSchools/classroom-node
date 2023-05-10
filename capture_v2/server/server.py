from functools import partial
from http import server
import io
import logging
import socketserver
import threading

from capture_v2.log import logger

PAGE = """\
<html>
<head>
<title>Camera Streamer</title>
</head>
<body>
<h1>Camera Streamer</h1>
<img src="stream.mjpg" width="640" height="360" />
</body>
</html>
"""


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class StreamingHandler(server.BaseHTTPRequestHandler):
    def __init__(self, streaming_output: StreamingOutput, *args, **kwargs):
        self.streaming_output = streaming_output

        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path == "/":
            self.send_response(301)
            self.send_header("Location", "/index.html")
            self.end_headers()
        elif self.path == "/index.html":
            content = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        elif self.path == "/stream.mjpg":
            self.send_response(200)
            self.send_header("Age", 0)
            self.send_header("Cache-Control", "no-cache, private")
            self.send_header("Pragma", "no-cache")
            self.send_header(
                "Content-Type", "multipart/x-mixed-replace; boundary=FRAME"
            )
            self.end_headers()
            try:
                while True:
                    if self.streaming_output is None:
                        self.send_error(404)

                    with self.streaming_output.condition:
                        self.streaming_output.condition.wait()
                        frame = self.streaming_output.frame
                    self.wfile.write(b"--FRAME\r\n")
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b"\r\n")
            except Exception as e:
                logging.warning(
                    "Removed streaming client %s: %s", self.client_address, str(e)
                )
        else:
            self.send_error(404)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, host: str = "", port: int = 8000, *args, **kwargs) -> None:
        self.host = host
        self.port = port

        self.started = False
        self.stop_event: threading.Event = threading.Event()
        self.server_thread: threading.Thread = None
        self.streaming_output: StreamingOutput = StreamingOutput()

        streaming_handler_class = partial(StreamingHandler, self.streaming_output)

        super().__init__(
            server_address=(self.host, self.port),
            RequestHandlerClass=streaming_handler_class,
            *args,
            **kwargs
        )

    def _start_thread(self) -> None:
        while not self.stop_event.is_set():
            try:
                self.serve_forever()
            finally:
                self.server_close()

    def start(self, background: bool = False) -> None:
        logger.info("Starting http server...")
        if background:
            self.server_thread = threading.Thread(
                target=self._start_thread, daemon=False
            )
            self.server_thread.start()
        else:
            self.serve_forever()

        self.started = True
        logger.info("Started http server")

    def stop(self) -> None:
        self.stop_event.set()
        if self.server_thread is not None and self.server_thread.is_alive():
            self.shutdown()
            self.server_thread.join()
        else:
            if self.started:
                self.shutdown()
        self.stop_event.clear()
        self.started = False
