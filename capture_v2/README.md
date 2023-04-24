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

## Configure pyenv (doesn't work)

### Install Pyenv (doesn't work)

https://www.ianwootten.co.uk/2021/11/29/how-to-setup-raspberry-pi-os-bullseye-like-a-python-pro/

```
sudo apt-get update; sudo apt-get install -y make build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init --path)"' >> ~/.bashrc
echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc

exec $SHELL

pyenv update
pyenv install 3.10
pyenv local system
pyenv virtualenv --system-site-packages 3.10.11 wf_camera
```


### Install picamera2 in pyenv environment (doesn't work)
```
sudo apt install -y python3-libcamera python3-kms++
sudo apt install -y python3-prctl libatlas-base-dev ffmpeg libopenjp2-7 python3-pip
sudo apt install build-essential libcap-dev

pip3 install numpy --upgrade
pip3 install picamera2
pip3 install python3-libcamera
pip3 install opencv-python
pip3 install pandas
pip3 install pydantic
pip install --force-reinstall --no-deps --ignore-requires-python interval-timer
```