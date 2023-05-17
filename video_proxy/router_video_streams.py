import io

import av
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from .log import logger

router = APIRouter(tags=["MJPEG Streaming Proxy"], responses={404: {"description": "Not found"}})


@router.get("/stream", response_class=StreamingResponse)
def stream():
    video_buffer = io.BytesIO()
    output_container = av.open(video_buffer, 'w', 'mjpeg')
    output_video_stream = output_container.add_stream('mjpeg')

    def read_input():
        container = av.open('http://192.168.50.229:8000/stream.mjpg')
        #yield container.demux()
        for packet in container.demux():
            for frame in packet.decode():
                # yield bytearray(frame.planes[0])
                img = frame.to_image()
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                img_byte_arr.seek(0)
                # yield img_byte_arr.getvalue()

                yield (
                        b'--FRAME\r\n' b'Content-Type: image/jpeg\r\n\r\n' + img_byte_arr.getvalue() + b'\r\n'
                )
                # yield b''+bytearray(frame.to_image())
                #yield frame
                # yield output_video_stream.encode(frame)
                # yield output_video_stream.encode(frame)
                # for p in output_packets:
                #     if p:
                #         yield output_container.mux(p)

    return StreamingResponse(read_input(),
                             media_type="multipart/x-mixed-replace; boundary=FRAME",
                             headers={
                                 "Content-Type": "image/jpeg",
                                 "Cache-Control": "no-cache, private",
                                 "Pragma": "no-cache",
                             },
                             status_code=200)
