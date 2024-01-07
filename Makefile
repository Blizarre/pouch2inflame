docker_build:
	docker buildx build . -t converter:latest

docker_build_arm:
	docker buildx build . -f Dockerfile.arm64 -t converter:latest

docker_shell:
	docker run -it converter:latest

prep-commit:
	black .
	isort .
	pylint *.py --disable=C0114,C0115,C0116
