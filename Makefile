VERSION ?= 0


build-capture:
#	docker buildx create --name multiarch
#	docker buildx use multiarch
#	docker buildx build -t wildflowerschools/classroom-node-capture:v${VERSION} --platform linux/arm64,linux/arm/v7 -f capture/Dockerfile --push .
#	docker buildx rm multiarch
	docker build -t wildflowerschools/classroom-node-capture:v${VERSION} -f capture/Dockerfile .
	docker push wildflowerschools/classroom-node-capture:v${VERSION}

build-scheduler:
	docker buildx create --name multiarch
	docker buildx use multiarch
	docker buildx build -t wildflowerschools/k8s-task-scheduler:v${VERSION} --platform linux/amd64,linux/arm64,linux/arm/v7 -f scheduler/Dockerfile --push .
	docker buildx rm multiarch
