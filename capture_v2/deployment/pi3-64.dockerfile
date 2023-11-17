FROM balenalib/raspberrypi3-64-python:3.9-bullseye as build-stage

RUN apt update -y && \
    apt remove python3-numpy -y && \
    apt install --no-install-recommends -y \
    build-essential \
    git \
    automake \
    autoconf \
    libtool \
    libffi-dev \
    wget \
    gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

## Install mp4fpsmod
RUN git clone https://github.com/nu774/mp4fpsmod.git && \
    cd mp4fpsmod && \
    ./bootstrap.sh && \
    ./configure && make && strip mp4fpsmod && \
    sudo make install

# Install yq
RUN wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_arm && \
    chmod a+x /usr/local/bin/yq

# Add piwheels to pip repositories, update pip, and install poetry
RUN printf "[global]\nextra-index-url=https://www.piwheels.org/simple\n" > /etc/pip.conf && \
    pip install --no-cache-dir --upgrade pip poetry wheel watchdog psutil


FROM balenalib/raspberrypi3-64-python:3.9-bullseye

ENV UDEV=on

RUN adduser --disabled-password --gecos '' docker && usermod -a -G tty,video docker

RUN apt update -y && \
    apt remove python3-numpy -y && \
    apt install --no-install-recommends -y \
    build-essential \
    libcamera-dev \
    python3 \
    python3-picamera2 \
    v4l-utils \
    ffmpeg \
    avahi-daemon \
    libnss-mdns \
    gcc \
    linux-headers \
    linux-libc-dev && \
    rm -rf /var/lib/apt/lists/*

COPY --from=build-stage /usr/local/bin/mp4fpsmod /usr/local/bin/wheel /usr/local/bin/pip /usr/local/bin/poetry /usr/local/bin/yq /usr/local/bin/
COPY --from=build-stage /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages

# Add multicast DNS for easier network identification
RUN set -ex \
 && echo '*' > /etc/mdns.allow \
 && sed -i "s/hosts:.*/hosts:          files mdns4 dns/g" /etc/nsswitch.conf

RUN mkdir /app && chown -R docker:docker /app
WORKDIR app

COPY pyproject.toml poetry.lock ./

# Need to remove the pre-built numpy, upgrading for whatever reason does not work
RUN pip uninstall numpy -y && poetry config virtualenvs.create false && poetry install --no-cache --only capture_v2 --no-root --no-interaction --no-ansi

COPY capture_v2 ./capture_v2
COPY capture_v2/scripts/entry-point.sh entry-point.sh

ENTRYPOINT ["/app/entry-point.sh"]
CMD ["python -m capture_v2"]
