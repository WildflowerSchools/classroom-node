
build-collector:
	docker build -t classroom-node-collector:wip -f docker/local/collector/Dockerfile .

run-collector:
	docker run -it --privileged --net=host -v $$PWD:/app classroom-node-collector:wip sh
