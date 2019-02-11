# Setting up the rpi

## Install docker

```
curl -sSL https://get.docker.com | sh
```

## update permission

Need to consider the security implications for this.

```
sudo usermod -aG docker pi
```


## start the docker daemon

```
sudo systemctl start docker
```

## install docker-compose

```
sudo pip3 install docker-compose
```

## docker images I know we want

```
docker pull redis:5-alpine
docker pull python:3.7-alpine
```


Random stuff
```
apk add --update alpine-sdk glib glib-dev linux-headers
pip install git+https://github.com/WildflowerSchools/graphql-python-client-generator.git
pip install git+https://github.com/WildflowerSchools/wildflower-honeycomb-sdk-py.git
pip install decawave-ble tenacity celery
```
