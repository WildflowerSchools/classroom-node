FROM --platform=linux/amd64 ubuntu:20.04

ARG REPO_NAME

ENV TZ=UTC
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt update && apt upgrade -y && \
    apt install wget sudo software-properties-common iproute2 net-tools dnsutils curl -y

RUN useradd -m docker && echo "docker:docker" | chpasswd && adduser docker sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers

WORKDIR /cdp-logger

USER docker

ADD install-custom.sh /cdp-logger

RUN REPO_NAME=$REPO_NAME bash install-custom.sh

ADD cdp-player.sh \
    cdplog-2022-11-14.00 /cdp-logger/
RUN sudo mv cdplog-2022-11-14.00 cdplog.00

CMD ["/cdp-logger/cdp-player.sh"]
