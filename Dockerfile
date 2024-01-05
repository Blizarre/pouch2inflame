# pull official base image
FROM debian:bookworm

RUN useradd -ms /bin/bash app

RUN --mount=id=aptextractor,sharing=private,type=cache,target=/var/cache/apt \
    apt-get update && apt-get -y install --no-install-recommends --no-install-suggests \
    pandoc npm

WORKDIR /opt/extractor
COPY extractor/package-lock.json extractor/package.json .
COPY extractor/src/cli.js ./src/cli.js

run npm install -g
USER app
