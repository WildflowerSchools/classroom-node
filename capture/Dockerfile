FROM wildflowerschools/classroom-node-capture:v45

# FROM balenalib/raspberrypi3-python:3.9-sid
#
# RUN mkdir /app
# RUN mkdir /out
#
# RUN apt update
# RUN apt install ffmpeg
#
#
# COPY ./capture/requirements.txt requirements.txt
#
# RUN READTHEDOCS=True pip install -r requirements.txt
#
# COPY ./capture/ /app/capture
# COPY ./run_capture.py /app/run_capture.py
# COPY ./run_upload.py /app/run_upload.py
#
# WORKDIR /app

COPY ./capture/ /app/capture
COPY ./run_capture.py /app/run_capture.py
COPY ./run_upload.py /app/run_upload.py

CMD ["python", "run_capture.py"]
