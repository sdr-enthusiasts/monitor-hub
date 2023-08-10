#!/bin/python3

import docker

client = docker.from_env()
client.containers.list()
