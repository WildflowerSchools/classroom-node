.PHONY: build-capture lint-capture build-cuwb-stream build-scheduler build-cdp-player run-cdp-player


build-capture: lint-capture
	-sudo docker buildx rm multiarch
	sudo docker buildx create --name multiarch
	sudo docker buildx use multiarch
	sudo docker buildx build -t wildflowerschools/classroom-node-capture:v$(shell cat capture/VERSION) --platform linux/arm/v7 -f capture/Dockerfile --push .
	sudo docker buildx rm multiarch

lint-capture:
	@pylint capture

build-cuwb-stream:
	-sudo docker buildx rm multiarch
	sudo docker buildx create --name multiarch
	sudo docker buildx use multiarch
	sudo docker buildx build --platform linux/amd64,linux/arm64,linux/arm/v7 -t wildflowerschools/classroom-cuwb-stream:v$(shell cat cuwb_stream/VERSION) -f cuwb_stream/Dockerfile --push .
	sudo docker buildx rm multiarch

build-scheduler:
	-sudo docker buildx rm multiarch
	sudo docker buildx create --name multiarch
	sudo docker buildx use multiarch
	sudo docker buildx build -t wildflowerschools/k8s-task-scheduler:v$(shell cat scheduler/VERSION) --platform linux/amd64,linux/arm64,linux/arm/v7 -f scheduler/Dockerfile --push .
	sudo docker buildx rm multiarch

build-cdp-player:
	if [ -z "$(REPO_NAME)" ]; then \
		echo "Cmd line arg 'REPO_NAME' missing. Required to download from proper Ciholas PPA."; \
		exit 1; \
	fi
	docker build -f ./cuwb_stream/tests/cdp_player/cdp-player.dockerfile -t cdp-player --build-arg REPO_NAME=${REPO_NAME} ./cuwb_stream/tests/cdp_player

run-cdp-player: build-cdp-player
	docker run -it --name cdp-player --net host --rm cdp-player