# pull official base image
FROM python:3-slim


# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN useradd -ms /bin/bash app

RUN --mount=type=cache,target=/var/cache/apt \
    apt-get update && apt-get -y install pandoc npm

WORKDIR /opt/convert
RUN --mount=type=bind,source=./convert/package-lock.json,target=package-lock.json \
    npm ci

COPY convert/main.js .
USER app