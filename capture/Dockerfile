FROM balenalib/raspberrypi3-python:3.9-buster

RUN mkdir /app
RUN mkdir /out

RUN apt update
RUN apt install ffmpeg


RUN set -ex \
 && apt-get update && apt-get install -y --no-install-recommends avahi-daemon libnss-mdns \
 # allow hostnames with more labels to be resolved. so that we can
 # resolve node1.mycluster.local.
 # (https://github.com/lathiat/nss-mdns#etcmdnsallow)
 && echo '*' > /etc/mdns.allow \
 # Configure NSSwitch to use the mdns4 plugin so mdns.allow is respected
 && sed -i "s/hosts:.*/hosts:          files mdns4 dns/g" /etc/nsswitch.conf

COPY ./capture/requirements.txt requirements.txt

RUN READTHEDOCS=True pip install -r requirements.txt

COPY ./capture/ /app/capture
COPY ./run_capture.py /app/run_capture.py
COPY ./run_upload.py /app/run_upload.py
COPY ./entry-point.sh /app/entry-point.sh

RUN chmod +x /app/entry-point.sh

WORKDIR /app

ENTRYPOINT ["./entry-point.sh"]

CMD ["python", "run_capture.py"]
