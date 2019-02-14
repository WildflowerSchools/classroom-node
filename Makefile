
build-collector:
	docker build -t classroom-node-collector:wip -f docker/local/collector/Dockerfile .

run-collector:
	docker run -it --privileged --net=host -v $$PWD:/app classroom-node-collector:wip sh


build-capture:
	docker build -t classroom-node-capture:wip -f docker/local/capture/Dockerfile .

run-capture:
	docker run -it --privileged --net=host -v $$PWD:/app classroom-node-capture:wip python run_capture.py
