#!/bin/bash

# Clean up the install dir
rm -rf ./rootfs/monitor-hub/static/js/* || exit 1


# recreate the dir structure

mkdir -p ./rootfs/monitor-hub/static/js || exit 1

cp ./dist/* ./rootfs/monitor-hub/static/js || exit 1
