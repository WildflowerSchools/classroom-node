FROM python:3.7-alpine

RUN apk add --update alpine-sdk glib glib-dev linux-headers

RUN mkdir /app
WORKDIR /app


COPY ./scheduler/requirements.txt /app/requirements.txt

RUN pip install -r requirements.txt

COPY ./scheduler/ /app/scheduler

CMD ["python", "-m", "scheduler"]
