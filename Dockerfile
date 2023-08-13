FROM node:20.5.0-slim AS typescript-builder
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY / /
RUN set -xe && \
    npm install && \
    npm run build

FROM ghcr.io/sdr-enthusiasts/docker-baseimage:python-test-pr
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2 \
    VERBOSE_LOGGING="false"

COPY rootfs/ /

# hadolint ignore=SC1091
RUN set -x && \
    TEMP_PACKAGES=() && \
    KEPT_PACKAGES=() && \
    KEPT_PACKAGES+=(ca-certificates) && \
    KEPT_PACKAGES+=(curl) & \
    KEPT_PACKAGES+=(gnupg) && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    "${KEPT_PACKAGES[@]}" \
    "${TEMP_PACKAGES[@]}" \
    && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    chmod a+r /etc/apt/keyrings/docker.gpg && \
    echo \
    "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
    "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update && \
    apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin -y --no-install-recommends  && \
    pushd /monitor-hub && \
    python3 -m pip install --no-cache-dir --break-system-packages -r requirements.txt && \
    # Clean up
    rm -rf /src/* /tmp/* /var/lib/apt/lists/*

COPY --from=typescript-builder /dist/* /monitor-hub/static/js
