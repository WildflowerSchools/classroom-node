FROM python:3.7-alpine

RUN mkdir /app

COPY ./workers/requirements.txt requirements.txt

RUN pip install -r requirements.txt

WORKDIR /app
