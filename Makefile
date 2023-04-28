.PHONY: build-capture build-capture-v2 lint-capture format-capture-v2 build-cuwb-stream build-scheduler build-cdp-player run-cdp-player

format-capture-v2:
	black capture_v2

lint-capture:
	@pylint capture

build-capture: lint-capture
	-docker buildx rm multiarch
	docker buildx create --name multiarch
	docker buildx use multiarch
	docker buildx build -t wildflowerschools/classroom-node-capture:v$(shell cat capture/VERSION) --platform linux/arm/v7 -f capture/Dockerfile --push .
	docker buildx rm multiarch

build-capture-v2:
	-docker buildx rm multiarch
	docker buildx create --name multiarch
	docker buildx use multiarch
	# Build for Raspberry Pi 4 64bit
	docker buildx build --cache-from wildflowerschools/classroom-node-capture-v2:latest-raspberrypi4-64 \
	    --cache-to "type=inline" -t wildflowerschools/classroom-node-capture-v2:latest-raspberrypi4-64 \
	    -t wildflowerschools/classroom-node-capture-v2:v$(shell cat capture_v2/VERSION)-raspberrypi4-64 \
	    --platform linux/arm64/v8 -f capture_v2/pi4-64.dockerfile \
	    --push .
	# Build for Raspberry Pi 3 32bit
	docker buildx build --cache-from wildflowerschools/classroom-node-capture-v2:latest-raspberrypi3-32 \
	    --cache-to "type=inline" -t wildflowerschools/classroom-node-capture-v2:latest-raspberrypi3-32 \
	    -t wildflowerschools/classroom-node-capture-v2:v$(shell cat capture_v2/VERSION)-raspberrypi3-32 \
	    --platform linux/arm/v7 -f capture_v2/pi3-32.dockerfile \
	    --push .
	# Build for Raspberry Pi 3 64bit
	docker buildx build --cache-from wildflowerschools/classroom-node-capture-v2:latest-raspberrypi3-64 \
	    --cache-to "type=inline" \
	    -t wildflowerschools/classroom-node-capture-v2:latest-raspberrypi3-64 \
	    -t wildflowerschools/classroom-node-capture-v2:v$(shell cat capture_v2/VERSION)-raspberrypi3-64 \
	    --platform linux/arm/v7 -f capture_v2/pi3-64.dockerfile \
	    --push .
	docker buildx rm multiarch

lint-cuwb-stream:
	@pylint cuwb_stream

build-cuwb-stream: lint-cuwb-stream
	-docker buildx rm multiarch
	docker buildx create --name multiarch
	docker buildx use multiarch
	docker buildx build --platform linux/amd64,linux/arm64 -t wildflowerschools/classroom-cuwb-stream:v$(shell cat cuwb_stream/VERSION) -f cuwb_stream/Dockerfile --push .
	docker buildx rm multiarch

build-scheduler:
	-docker buildx rm multiarch
	docker buildx create --name multiarch
	docker buildx use multiarch
	docker buildx build -t wildflowerschools/k8s-task-scheduler:v$(shell cat scheduler/VERSION) --platform linux/amd64,linux/arm64,linux/arm/v7 -f scheduler/Dockerfile --push .
	docker buildx rm multiarch

build-cdp-player:
	if [ -z "$(REPO_NAME)" ]; then \
		echo "Cmd line arg 'REPO_NAME' missing. Required to download from proper Ciholas PPA."; \
		exit 1; \
	fi
	docker build -f ./cdp_player/cdp-player.dockerfile -t cdp-player --build-arg REPO_NAME=${REPO_NAME} ./cdp_player

run-cdp-player: build-cdp-player
	docker run -it --name cdp-player --net host --rm cdp-player
