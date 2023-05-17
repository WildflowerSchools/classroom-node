import io
import logging
import os

import av
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from .log import logger
from .proxy import Proxy, CameraStream

av.logging.set_level(logging.INFO)
router = APIRouter(tags=["MJPEG Streaming Proxy"], responses={404: {"description": "Not found"}})

proxy = Proxy()
proxy.add_stream(CameraStream(
    device_name="pi",
    device_id="pi",
    device_ip="192.168.50.229"))


@router.get("/stream", response_class=StreamingResponse)
def stream():
    def read_stream():
        while True:
            frame = next(proxy.read_stream(device_id="pi"))
            yield (
                    b'--FRAME\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
            )

    return StreamingResponse(read_stream(),
                             media_type="multipart/x-mixed-replace; boundary=FRAME",
                             headers={
                                 "Age": "0",
                                 "Cache-Control": "no-cache, private",
                                 "Pragma": "no-cache",
                             },
                             status_code=206)
