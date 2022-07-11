FROM balenalib/raspberrypi3-python:3.7

RUN mkdir /app
RUN mkdir /out

RUN apt update
RUN apt install ffmpeg


COPY ./capture/requirements.txt requirements.txt

RUN READTHEDOCS=True pip install -r requirements.txt

COPY ./capture/ /app/capture
COPY ./run_capture.py /app/run_capture.py
COPY ./run_upload.py /app/run_upload.py

WORKDIR /app


CMD ["python", "run_capture.py"]
