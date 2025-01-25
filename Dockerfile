FROM node:23.6.1-slim AS typescript-builder
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

COPY / /
RUN set -xe && \
    npm install && \
    npm run build

FROM ghcr.io/sdr-enthusiasts/docker-baseimage:python-test-pr
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2 \
    VERBOSE_LOGGING="false" \
    S6_LOGGING="0" \
    MONITOR_HUB_DATABASE_PATH="/run/monitor-hub/monitor-hub.sqlite"

COPY rootfs/ /
COPY /package.json /package.json

# hadolint ignore=SC1091
RUN set -x && \
    TEMP_PACKAGES=() && \
    KEPT_PACKAGES=() && \
    KEPT_PACKAGES+=(ca-certificates) && \
    KEPT_PACKAGES+=(curl) & \
    KEPT_PACKAGES+=(gnupg) && \
    KEPT_PACKAGES+=(nginx-light) && \
    TEMP_PACKAGES+=(build-essential) && \
    TEMP_PACKAGES+=(gcc) && \
    TEMP_PACKAGES+=(make) && \
    TEMP_PACKAGES+=(python3-dev) && \
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
    VERSION=$(cat /package.json| grep 'version' | cut -d '"' -f 4) && \
    echo "${VERSION}" > /CONTAINER_VERSION && \
    mkdir -p /run/monitor-hub && \
    # Clean up
    apt-get remove -y "${TEMP_PACKAGES[@]}" && \
    apt-get autoremove -y && \
    rm -rf /src/* /tmp/* /var/lib/apt/lists/* /package.json

COPY --from=typescript-builder /dist/* /monitor-hub/static/js
