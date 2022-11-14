FROM --platform=linux/amd64 ubuntu:20.04

ARG REPO_NAME

ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt update && apt upgrade -y && \
    apt install wget sudo software-properties-common iproute2 net-tools dnsutils -y

RUN useradd -m docker && echo "docker:docker" | chpasswd && adduser docker sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

#WORKDIR /cuwb_stream
#
#ADD cuwb_stream/ /cuwb_stream
#RUN pip install -r requirements.txt

WORKDIR /cdp-logger

USER docker

ADD install-custom.sh /cdp-logger

RUN REPO_NAME=$REPO_NAME bash install-custom.sh

ADD cdp-player.sh /cdp-logger
ADD cdplog-2022-11-08.00 /cdp-logger
#ADD cdplog-2022-10-28.01 /cdp-logger

CMD ["/cdp-logger/cdp-player.sh"]
