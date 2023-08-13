FROM node:20.5.0-slim AS typescript-builder
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY / /
RUN set -xe && \
    npm install && \
    npm run build

FROM ghcr.io/sdr-enthusiasts/docker-baseimage:python-test-pr
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2 \
    VERBOSE_LOGGING="false" \
    S6_LOGGING="0"

COPY rootfs/ /

# hadolint ignore=SC1091
RUN set -x && \
    TEMP_PACKAGES=() && \
    KEPT_PACKAGES=() && \
    KEPT_PACKAGES+=(ca-certificates) && \
    KEPT_PACKAGES+=(curl) & \
    KEPT_PACKAGES+=(gnupg) && \
    KEPT_PACKAGES+=(nginx-light) && \
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
    popd && \
    # set up nginx
    mkdir -p /var/log/nginx && \
    cp /etc/nginx.monitor-hub/sites-enabled/monitor-hub /etc/nginx/sites-enabled/monitor-hub && \
    rm /etc/nginx/sites-enabled/default && \
    rm /etc/nginx/nginx.conf && \
    cp /etc/nginx.monitor-hub/nginx.conf /etc/nginx/nginx.conf && \
    rm -rv /etc/nginx.monitor-hub && \
    # Clean up
    rm -rf /src/* /tmp/* /var/lib/apt/lists/*

COPY --from=typescript-builder /dist/* /monitor-hub/static/js
