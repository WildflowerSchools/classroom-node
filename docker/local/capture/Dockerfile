FROM python:3.7-alpine

RUN mkdir /app
RUN pip install --upgrade pip

COPY ./capture/requirements.txt requirements.txt

RUN pip install -r requirements.txt

WORKDIR /app
