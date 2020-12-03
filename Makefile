
build-collector:
	docker build -t classroom-node-collector:wip -f docker/local/collector/Dockerfile .

run-collector:
	docker run -it --privileged --net=host -v $$PWD:/app classroom-node-collector:wip sh


build-capture:
	docker build -t classroom-node-capture:wip -f docker/local/capture/Dockerfile .

run-capture:
	docker run -it --privileged --net=host -v $$PWD:/app classroom-node-capture:wip python run_capture.py

apply-dashboard:
	kubectl --context k3s apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v1.10.1/src/deploy/recommended/kubernetes-dashboard-arm.yaml
