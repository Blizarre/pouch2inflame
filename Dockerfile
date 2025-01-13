FROM debian:bookworm

RUN useradd -ms /bin/bash app

RUN --mount=id=aptextractor,sharing=private,type=cache,target=/var/cache/apt \
    apt-get update && apt-get -y install --no-install-recommends --no-install-suggests \
    pandoc npm gyp pkg-config libpixman-1-dev \
    libcairo2-dev libpangocairo-1.0-0 libpango1.0-dev build-essential

WORKDIR /opt/extractor
COPY extractor/package-lock.json extractor/package.json .
COPY extractor/src/cli.js ./src/cli.js

RUN npm install -g

USER app

