FROM balenalib/raspberrypi3-python:3.9-bullseye

ENV UDEV=on

RUN adduser --disabled-password --gecos '' docker && usermod -a -G tty,video docker

RUN apt update -y && \
    apt remove python3-numpy -y && \
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
    ffmpeg \
    libffi-dev \
    libssl-dev \
    libatlas-base-dev

# Add piwheels to pip repositories
RUN printf "[global]\nextra-index-url=https://www.piwheels.org/simple\n" > /etc/pip.conf
RUN pip install --upgrade pip poetry wheel

## Install mp4fpsmod
RUN (cd /tmp && \
     rm -rf mp4fpsmod && \
     git clone https://github.com/nu774/mp4fpsmod.git && \
     cd mp4fpsmod && \
     ./bootstrap.sh && \
     ./configure && make && strip mp4fpsmod && \
     sudo make install && \
     cd /tmp && rm -rf /tmp/mp4fpsmod)

RUN set -ex \
 && apt install -y --no-install-recommends avahi-daemon libnss-mdns \
 && echo '*' > /etc/mdns.allow \
 && sed -i "s/hosts:.*/hosts:          files mdns4 dns/g" /etc/nsswitch.conf

RUN rm -rf /var/lib/apt/lists/*

RUN mkdir /app && chown -R docker:docker /app
WORKDIR app

COPY pyproject.toml poetry.lock ./

#RUN apt install -y libatlas-base-dev
# Need to remove the pre-built numpy, upgrading for whatever reason does not work
# Also install packages that with known wheels for armv7 architecture
#RUN pip uninstall numpy -y && \
#    pip install numpy==1.24.2 pandas==2.0.0 pydantic==1.10.6
#
#RUN poetry export --only capture_v2 --without-hashes > requirements.txt && \
#    pip install --requirement requirements.txt #poetry config virtualenvs.create false && poetry install --only capture_v2 --no-root --no-interaction --no-ansi
RUN pip uninstall numpy -y && poetry config virtualenvs.create false && poetry install --no-cache --only capture_v2 --no-root --no-interaction --no-ansi

COPY capture_v2 ./capture_v2
COPY capture_v2/entry-point.sh entry-point.sh

ENTRYPOINT ["/app/entry-point.sh"]
CMD ["python -m capture_v2"]
