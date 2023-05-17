import random
import string

from . import errors
from .log import logger
from . import router_video_streams

from fastapi import Depends, FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
import fastapi.exceptions as fastapiExceptions
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import requests

app = FastAPI(title="Classroom Video Proxy", root_path="/")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def tag_request(request: Request, call_next):
    idem = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    request.state.idem = idem

    response = await call_next(request)

    return response


async def log_request_details(request: Request):
    headers = "\r\n\t".join("{}: {}".format(k, v) for k, v in request.headers.items())
    body = await request.body()
    logger.info(
        """rid={rid} details
    {method} {url}

    HEADERS:
    {headers}

    BODY:
    {body}
    """.format(
            rid=request.state.idem, method=request.method, url=request.url, headers=headers, body=body.decode("utf-8")
        )
    )

app.include_router(router_video_streams.router, dependencies=[Depends(log_request_details)])


@app.get("/")
async def hola_mundo():
    return JSONResponse(content={"message": "¡Hola, mundo!"})


@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def resource_not_found(request, ex):
    logger.warning(f"Handle 404 exception: {ex}")
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": ex.detail if hasattr(ex, "detail") else "Not Found"})


@app.exception_handler(requests.exceptions.HTTPError)
async def request_unexpected_http_exception(request, ex):
    logger.warning(f"Handle unexpected {ex.response.status_code} exception: {ex}")
    return JSONResponse(status_code=ex.response.status_code, content=None)


@app.exception_handler(errors.SignatureError)
async def handle_signature_error(request, ex):
    logger.warning(f"Handle 401 exception: {ex}")
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=jsonable_encoder({"detail": ex.error}))


@app.exception_handler(fastapiExceptions.RequestValidationError)
async def handle_request_validation_error(request, ex):
    logger.warning(f"Handle 422 exception: {ex}")
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=jsonable_encoder({"detail": ex.errors(), "body": ex.body}))


@app.exception_handler(Exception)
async def handle_general_exception(request, ex):
    logger.error(f"Handle 500 exception: {ex}")
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=jsonable_encoder({"detail": "Unexpected server error"}))
