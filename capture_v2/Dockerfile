FROM balenalib/raspberrypi4-64-python:3.9-bullseye

ENV UDEV=on

RUN adduser --disabled-password --gecos '' docker && usermod -a -G tty,video docker

RUN apt update -y && sudo apt upgrade && \
    apt install -y \
    build-essential \
    libcamera-dev \
    python3 \
    python3-picamera2 --no-install-recommends \
    v4l-utils \
    git \
    automake \
    autoconf \
    libtool \
    ffmpeg && \
    pip install --upgrade pip poetry wheel

# Install mp4fpsmod
RUN (cd /tmp && \
     rm -rf mp4fpsmod && \
     git clone https://github.com/nu774/mp4fpsmod.git && \
     cd mp4fpsmod && \
     ./bootstrap.sh && \
     ./configure && make && strip mp4fpsmod && \
     sudo make install)

RUN set -ex \
 && apt install -y --no-install-recommends avahi-daemon libnss-mdns \
 && echo '*' > /etc/mdns.allow \
 && sed -i "s/hosts:.*/hosts:          files mdns4 dns/g" /etc/nsswitch.conf

RUN mkdir /app && chown -R docker:docker /app
WORKDIR app

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && poetry install --only capture_v2 --no-root --no-interaction --no-ansi

COPY capture_v2 ./capture_v2
COPY capture_v2/entry-point.sh entry-point.sh

ENTRYPOINT ["/app/entry-point.sh"]
CMD ["python -m capture_v2"]
