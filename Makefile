docker_build:
	docker buildx build . -t converter:latest

docker_shell:
	docker run -it converter:latest

prep-commit:
	black .
	isort .
	pylint *.py --disable=C0114,C0115,C0116
