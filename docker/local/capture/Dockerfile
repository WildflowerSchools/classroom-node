FROM balenalib/raspberrypi3-python:3.6

RUN mkdir /app
RUN mkdir /out

RUN pip install --upgrade pip

COPY ./capture/requirements.txt requirements.txt

RUN pip install -r requirements.txt

RUN apt-get update
RUN apt-get install git

RUN pip install git+https://github.com/WildflowerSchools/graphql-python-client-generator.git
RUN pip install git+https://github.com/WildflowerSchools/wildflower-honeycomb-sdk-py.git

WORKDIR /app
