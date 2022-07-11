.PHONY: build-capture lint-capture build-cuwb-stream build-scheduler


build-capture: lint-capture
	VERSION := $(shell cat capture/VERSION)
	docker buildx create --name multiarch
	docker buildx use multiarch
	docker buildx build -t wildflowerschools/classroom-node-capture:v${VERSION} --platform linux/arm64,linux/arm/v7 -f capture/Dockerfile --push .
	docker buildx rm multiarch

lint-capture:
	@pylint capture



build-cuwb-stream:
	VERSION := $(shell cat cuwb_stream/VERSION)
	docker buildx create --name multiarch
	docker buildx use multiarch
	docker buildx build --platform linux/amd64,linux/arm64,linux/arm/v7 -t wildflowerschools/classroom-cuwb-stream:v${VERSION} -f cuwb_stream/Dockerfile --push .
	docker buildx rm multiarch

build-scheduler:
	VERSION := $(shell cat scheduler/VERSION)
	docker buildx create --name multiarch
	docker buildx use multiarch
	docker buildx build -t wildflowerschools/k8s-task-scheduler:v${VERSION} --platform linux/amd64,linux/arm64,linux/arm/v7 -f scheduler/Dockerfile --push .
	docker buildx rm multiarch
