FROM python:3.6-alpine

RUN apk add --update alpine-sdk glib glib-dev linux-headers

RUN mkdir /app

RUN pip install --upgrade pip

COPY ./workers/requirements.txt requirements.txt

RUN pip install -r requirements.txt

RUN pip install git+https://github.com/WildflowerSchools/graphql-python-client-generator.git
RUN pip install git+https://github.com/WildflowerSchools/wildflower-honeycomb-sdk-py.git


WORKDIR /app
