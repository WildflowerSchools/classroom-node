FROM balenalib/raspberrypi3-python:3.6

RUN mkdir /app
RUN mkdir /out

RUN apt update
RUN apt install ffmpeg


COPY ./capture/requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY ./camnode/ /app/camnode
COPY ./capture/ /app/capture
COPY ./run_capture.py /app/run_capture.py

WORKDIR /app


CMD ["python", "run_capture.py"]