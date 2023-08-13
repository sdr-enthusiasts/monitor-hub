# Monitor Hub

## Overview

Monitor Hub is a simple docker container that enables you to view logs from all of the running docker services. It was created to make it easier for users of the SDR-E (and probably any docker user) to view the logs of all of the running services in one place without SSH-ing in to the box and running `docker logs` on each container.

## Usage / Getting Started

```yaml
  monitor-hub:
    image: ghcr.io/sdr-enthusiasts/monitor-hub:latest
    tty: true
    container_name: monitor-hub
    restart: always
    ports:
      - 80:80
    environment:
      - TZ=${FEEDER_TZ}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    tmpfs:
      - /run:exec,size=64M
      - /var/log
      - /tmp
```

Likely you will need to amend the port line if port `80` is in use on your host or in docker.

## Limitations and Future Improvements

***If you have a large stack of containers, OR you have containers that contain a significant number of log entries, the page will not be available until all log entries are processed. This may take a minute or two to accomplish***

Currently, the container will show up to 100 lines of logs (50 on page load) from each container. This is done to save infinite scrolling and bandwidth. This will be improved by adding a "load more" (or simililar idea) button in the future.

The webpage is a bit basic. While this entire project doesn't need much complication, it's a bit basic for my liking.

The webpage is unusable on mobile. This will be improved in future versions.

The page does not auto-scroll to the bottom. This will be improved in future versions.

If a container SHOULD be running, but it is not, the webpage will not show it. This will be improved in future versions.

A potential future improvement would be to add a search bar to filter the containers shown or log entries.

Another potential future improvement would be to clean up log entries by removing the container-added time stamp and using the docker daemon one. If you see two time stamps, it's because of this.

A last future potential improvement would be to enable some level of container management, ie pulling new images, stopping/restarting, etc.
