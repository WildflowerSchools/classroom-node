# capture_v2

Raspberry PI capture using `picamera2` library. This is Python's newest camera library. It is is built on `libcamera`. This library must be run on Bullseye OS. 

## Run with Docker
1. Install Docker on Host
```
(cd /tmp && \
curl -fsSL https://get.docker.com -o get-docker.sh && \
sudo sh get-docker.sh && \
sudo groupadd -f docker && \
sudo usermod -aG docker $USER && \
newgrp docker && \
sudo chown "$USER":"$USER" /home/"$USER"/.docker -R && \ 
sudo chmod g+rwx "$HOME/.docker" -R)
```

2. Create Capture Output Directory on Host
```
sudo mkdir -p /data/capture_output
sudo chown "$USER":"$USER" /data/capture_output
```

3. Run Containers
```
docker run -d \
    --privileged \
    -p 8000:8000 \
    -e MINIO_ENABLE=false \
    -e CAMERA_V_FLIP=yes \
    -e CAMERA_H_FLIP=yes \
    -e HONEYCOMB_CLIENT_ID=EM2pKhXppSchfOW3v0Mp8gn9MVrFn2Mr \
    -e HONEYCOMB_CLIENT_SECRET=<<SECRET>> \
    -v /run/udev:/run/udev:ro \
    -v /data/capture_output:/app/output \
    -v /boot:/boot \
    wildflowerschools/classroom-node-capture-v2:v43-raspberrypi4-64
```

Run Minio
```
docker run \
   -d \
   -p 9000:9000 \
   -p 9090:9090 \
   --name minio \
   -v ~/minio/data:/data \
   -e "MINIO_ROOT_USER=root" \
   -e "MINIO_ROOT_PASSWORD=password1" \
   quay.io/minio/minio server /data --console-address ":9090"
```

4. 
Navigate to `http://<<RASPERBERRY PI IP ADDRESS>>:8000/stream.mjpg` to see a live MJPEG stream of the camera

By default, 10 second camera snippets in mp4 format will be written to `/data/capture_output`


5. Build and run container using local repo

```
docker build -f ./capture_v2/deployment/pi4-64.dockerfile -t wildflowerschools/classroom-node-capture-v2:local .
```

```
docker run \
    --privileged \
    --rm \
    -p 8000:8000 \
    -e MINIO_ENABLE=false \
    -e CAMERA_V_FLIP=yes \
    -e CAMERA_H_FLIP=yes \
    -e VIDEO_CLIP_OUTPUT_DIR=/app/out \
    -e HONEYCOMB_CLIENT_ID=EM2pKhXppSchfOW3v0Mp8gn9MVrFn2Mr \
    -e HONEYCOMB_CLIENT_SECRET=<<SECRET>> \
    --mount 'type=bind,src=/run/udev,dst=/run/udev,readonly' \
    --mount 'type=bind,src=/boot,dst=/boot,readonly' \
    wildflowerschools/classroom-node-capture-v2:local
```

## Run on Pi Host

1. Install mp4fpsmod
```
sudo apt update && sudo apt install autoconf libtool libcap-dev -y

(cd /tmp &&
rm -rf mp4fpsmod &&
git clone https://github.com/nu774/mp4fpsmod.git &&
cd mp4fpsmod &&
./bootstrap.sh &&
./configure && make && strip mp4fpsmod &&
sudo make install)
```

2. Install Poetry

```
curl -sSL https://install.python-poetry.org | python3 -
```

2. Install Dependencies
```
export PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring
poetry install --only capture_v2
pip install picamera2
rm -rf `poetry env info -p`/lib/python3.9/site-packages/picamera2
cp -r /usr/lib/python3/dist-packages/picamera2* `poetry env info -p`/lib/python3.9/site-packages/
cp -r /usr/lib/python3/dist-packages/v4l2* `poetry env info -p`/lib/python3.9/site-packages/
cp -r /usr/lib/python3/dist-packages/libcamera* `poetry env info -p`/lib/python3.9/site-packages/
cp -r /usr/lib/python3/dist-packages/pykms* `poetry env info -p`/lib/python3.9/site-packages/
pip install python-prctl piexif pidng


poetry run python -m capture_v2
```


3. Run as Module

```
python -m capture_v2 
```

4. Verify

Navigate to `http://<<RASPERBERRY PI IP ADDRESS>>:8000/stream.mjpg` to see a live MJPEG stream of the camera

By default, 10 second camera snippets in mp4 format will be written to `./output`

###