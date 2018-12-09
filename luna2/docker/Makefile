TAG := "localhost:5000/luna:latest"
build:
	docker build -t ${TAG} .
	docker push ${TAG}

run:
	mkdir -p ./{data,logs,conf}
	docker run --rm -d \
		--name luna \
		-e GUNICORN_CMD_ARGS="--config /etc/gunicorn/gunicorn.conf" \
		--env-file environment-vars \
		-v "$(shell pwd)/data:/data" \
		-v "$(shell pwd)/logs:/logs" \
		-v "$(shell pwd)/../luna:/luna" \
		-p 6000:7050 \
		localhost:5000/luna:latest
	docker exec -it luna /bin/bash

clean:
	docker kill luna || true
	rm -rf ./{data,logs} || true
