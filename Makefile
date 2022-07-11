.PHONY: show-version

VERSION := $(shell cat VERSION)

show-version:
	@echo $(VERSION)

build-capture: lint-capture
	docker buildx create --name multiarch
	docker buildx use multiarch
	docker buildx build -t wildflowerschools/classroom-node-capture:v${VERSION} --platform linux/amd64,linux/arm64 -f capture/Dockerfile --push .
	docker buildx rm multiarch

lint-capture:
	@pylint capture



build-cuwb-stream:
	docker buildx create --name multiarch
	docker buildx use multiarch
	docker buildx build --platform linux/amd64,linux/arm64,linux/arm/v7 -t wildflowerschools/classroom-cuwb-stream:v${VERSION} -f cuwb_stream/Dockerfile --push .
	docker buildx rm multiarch

build-scheduler:
	docker buildx create --name multiarch
	docker buildx use multiarch
	docker buildx build -t wildflowerschools/k8s-task-scheduler:v${VERSION} --platform linux/amd64,linux/arm64,linux/arm/v7 -f scheduler/Dockerfile --push .
	docker buildx rm multiarch
