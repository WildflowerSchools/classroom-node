# Ciholas CDP Player

Designed to run on Docker for Mac

* TODO: Test and update to run on Docker Linux
* TODO: Turn hardcoded values into ars: UDP Port, whether player loops, speed at which player runs back logs, path to the logfile to playback

## Build

```
docker build -f cdp-player.dockerfile -t cdp-player --build-arg REPO_NAME=<<Ciholas PPA Repository Name>> .
```

## Run

Container will playback logs on the host network (0.0.0.0) over UDP port 7667

```
docker run -it --name cdp-player --net host --rm cdp-player
```
