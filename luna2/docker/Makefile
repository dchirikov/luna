TAG := "localhost:5000/luna:latest"
build:
	docker build -t ${TAG} .
	docker push ${TAG}

run:
	mkdir -p ./{data,logs,conf}
	docker run --rm -d \
		--name luna \
		-v "$(shell pwd)/data:/data" \
		-v "$(shell pwd)/logs:/logs" \
		-v "$(shell pwd)/conf:/conf" \
		-v "$(shell pwd)/../luna:/luna" \
		-p 6000:6000 \
		localhost:5000/luna:latest
	#docker exec -it luna /bin/bash

clean:
	docker kill luna || true
	rm -rf ./{data,logs} || true
