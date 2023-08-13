#!/bin/bash

docker stop monitor-hub
docker rm monitor-hub
docker run -d --name monitor-hub -v /var/run/docker.sock:/var/run/docker.sock -p 80:80 -p 8888:8888 fredclausen/monitor-hub
