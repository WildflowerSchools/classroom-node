import os

from picamera2 import Picamera2
from picamera2.encoders import Encoder
from picamera2.picamera2 import _log
from picamera2.job import Job

from capture_v2.log import logger


class WFPicamera2(Picamera2):
    def __init__(self, camera_num=0, verbose_console=None, tuning=None):
        super().__init__(camera_num=camera_num, verbose_console=verbose_console, tuning=tuning)

        self._encoders = set()
        self._stream_type_map = {}

    def add_encoder(self, encoder: Encoder, stream_type: str):
        with self.lock:
            self._encoders.add(encoder)
            self._stream_type_map[encoder] = stream_type

    def remove_encoder(self, encoder: Encoder):
        if encoder.running:
            encoder.stop()

        with self.lock:
            self._stream_type_map.pop(encoder)
            self._encoders.remove(encoder)
            

    def process_requests(self, display) -> None:
        # This is the function that the event loop, which runs externally to us, must
        # call.
        requests = []
        with self._requestslock:
            requests = self._requests
            self._requests = []
        self.frames += len(requests)
        # It works like this:
        # * We maintain a list of the requests that libcamera has completed (completed_requests).
        #   But we keep only a minimal number here so that we have one available to "return
        #   quickly" if an application asks for it, but the rest get recycled to libcamera to
        #   keep the camera system running.
        # * The lock here protects the completed_requests list (because if it's non-empty, an
        #   application can pop a request from it asynchronously), and the _job_list. If
        #   we don't have a request immediately available, the application will queue a
        #   "job" for us to execute here in order to accomplish what it wanted.

        with self.lock:
            # These new requests all have one "use" recorded, which is the one for
            # being in this list.  Increase by one, so it cant't get discarded in
            # self.functions block.
            for req in requests:
                req.acquire()
            self.completed_requests += requests

            # This is the request we'll hand back to be displayed. This counts as a "use" too.
            display_request = None
            if requests:
                display_request = requests[-1]
                display_request.acquire()

            if self.pre_callback:
                for req in requests:
                    # Some applications may (for example) want us to draw something onto these images before
                    # encoding or copying them for an application.
                    self.pre_callback(req)

            # See if we have a job to do. When executed, if it returns True then it's done and
            # we can discard it. Otherwise it remains here to be tried again next time.
            finished_jobs = []
            while self._job_list:
                _log.debug(f"Execute job: {self._job_list[0]}")
                if self._job_list[0].execute():
                    finished_jobs.append(self._job_list.pop(0))
                else:
                    break

            # if self.encode_stream_name in self.stream_map:
            #     stream = self.stream_map[self.encode_stream_name]

            for req in requests:
                # Some applications may want to do something to the image after they've had a change
                # to copy it, but before it goes to the video encoder.
                if self.post_callback:
                    self.post_callback(req)

                for encoder in self._encoders:
                    if encoder in self._stream_type_map:
                        stream_type = self._stream_type_map[encoder]
                        stream = self.stream_map[stream_type]
                        if encoder.firsttimestamp is None:
                            fb = req.request.buffers[stream]
                            encoder_start_in_monotonic_seconds = (
                                fb.metadata.timestamp / 1e9
                            )

                            if hasattr(
                                encoder.output, "set_encoder_monotonic_start_time"
                            ):
                                encoder.output.set_encoder_monotonic_start_time(
                                    encoder_start_in_monotonic_seconds
                                )

                            logger.info(
                                f"Started encoder at monotonic time (in seconds) '{encoder_start_in_monotonic_seconds}'"
                            )
                            
                        encoder.encode(stream, req)

                req.release()

            # We hang on to the last completed request if we have been asked to.
            while len(self.completed_requests) > self._max_queue_len:
                self.completed_requests.pop(0).release()

        # If one of the functions we ran reconfigured the camera since this request came out,
        # then we don't want it going back to the application as the memory is not valid.
        if display_request is not None:
            if display_request.configure_count == self.configure_count and \
               display_request.config['display'] is not None:
                display.render_request(display_request)
            display_request.release()

        for job in finished_jobs:
            job.signal()

    def _run_process_requests(self):
        """Cause the process_requests method to run in the event loop again."""
        os.write(self.notifyme_w, b"\x00")

    def dispatch_functions(self, functions, wait, signal_function=None, immediate=False) -> None:
        """The main thread should use this to dispatch a number of operations for the event loop to perform.

        When there are multiple items each will be processed on a separate
        trip round the event loop, meaning that a single operation could stop and restart the
        camera and the next operation would receive a request from after the restart.
        """
        if wait is None:
            wait = signal_function is None
        with self.lock:
            only_job = not self._job_list
            job = Job(functions, signal_function)
            self._job_list.append(job)
            # If we're the only job now, and there are completed_requests queued up, then
            # it's worth prodding the event loop immediately as that request may be all we
            # need. We also prod the event loop if "immediate" is set, which can happen for
            # operations that begin by stopping the camera (such as mode switches, or simple
            # stop commands, for which no requests are needed).
            if only_job and (self.completed_requests or immediate):
                self._run_process_requests()
        return job.get_result() if wait else job # Consider using `job._future.result(timeout=X)` to force the job to complete after X seconds
    
    def capture_request(self, wait=None, signal_function=None):
        """Fetch the next completed request from the camera system.

        You will be holding a reference to this request so you must release it again to return it
        to the camera system.
        """
        functions = [self.capture_request_]
        return self.dispatch_functions(functions, wait, signal_function)
