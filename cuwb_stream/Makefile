.PHONY: build-cdp-player run-cdp-player

build-cdp-player:
	if [ -z "$(REPO_NAME)" ]; then \
		echo "Cmd line arg 'REPO_NAME' missing. Required to download from proper Ciholas PPA."; \
		exit 1; \
	fi
	docker build -f ../cdp_player/cdp-player.dockerfile -t cdp-player --build-arg REPO_NAME=${REPO_NAME} ../cdp_player

run-cdp-player:
	docker run -it --name cdp-player --net host --rm cdp-player