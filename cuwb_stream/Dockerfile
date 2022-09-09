FROM python:3.8.14-alpine

COPY ./cuwb_stream/requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY ./cuwb_stream/ /app/cuwb_stream

WORKDIR /app

CMD ["python", "-m", "cuwb_stream.tools", "collect", "--consumer", "stdout"]
