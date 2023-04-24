# capture_v2

Raspberry PI capture using `picamera2` library. This is Python's newest camera library. It is is built on `libcamera`. This library must be run on Bullseye OS. 

## Install

1. Install mp4fpsmod
```
sudo apt update && sudo apt install autoconf libtool -y

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
poetry install --only camera_v2
```


3. Run as Module

```
python -m capture_v2 
```

4. Verify

Navigate to `http://<<RASPERBERRY PI IP ADDRESS>>:8000/stream.mjpg` to see a live MJPEG stream of the camera

By default, 10 second camera snippets in mp4 format will be written to `./output`
