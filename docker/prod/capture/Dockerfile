FROM python:3.7-alpine

RUN mkdir /app

COPY ./requirements.txt requirements.txt

COPY .camnode/ /app/camnode
COPY .capture/ /app/capture

RUN pip install -r requirements.txt

WORKDIR /app
