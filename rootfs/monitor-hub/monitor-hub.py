#!/bin/python3

import eventlet

eventlet.monkey_patch()

import time
import docker
from threading import Thread
from flask_socketio import SocketIO
from flask import Flask, render_template, request, redirect, url_for
from signal import signal, SIGINT
from sys import exit

app = Flask(__name__)
# Make the browser not cache files if running in dev mode
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# turn the flask app into a socketio app
# regarding async_handlers=True, see: https://github.com/miguelgrinberg/Flask-SocketIO/issues/348
socketio = SocketIO(
    app,
    async_mode=None,
    async_handlers=True,
    logger=False,
    engineio_logger=False,
    ping_timeout=300,
    cors_allowed_origins="*",
)

# a list of threads

check_thread = None
container_threads = []
containers = []

keep_watching = True


class MonitorContainer:
    def __init__(self, name=""):
        self.name = name
        self.log = []

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    def __eq__(self, other):
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __ne__(self, other):
        return not (self == other)

    def get_log(self, num_lines=10):
        return self.log[-num_lines:]

    # function to monitor a container and append the logs for processing to clients
    # TODO: Capture and politely handle program exit

    def container_logs(self, container):
        for line in container.logs(stream=True):
            print(format_line(line.decode("utf-8"), container.name))
            self.log.append(format_line(line.decode("utf-8"), container.name))

        # the container has exited so we can remove it from the list
        print("Container {} has exited".format(container.name))
        containers.remove(container.name)


def exit_handler(signal_received, _):
    # Handle any cleanup here
    print(f"Exit signal {signal_received} detected. Exiting gracefully")
    keep_watching = False
    exit(0)


# line formatter
def format_line(line, container_name):
    return "{} | {}".format(container_name, line.strip())


def pause_and_check():
    while keep_watching:
        check_for_new_containers()
        time.sleep(5)


# function to check for new containers and start monitoring them
def check_for_new_containers():
    for container in docker.from_env().containers.list():
        if container.name not in containers:
            # create a thread for each container
            c = MonitorContainer(container.name)
            t = Thread(target=c.container_logs, args=(container,))
            print(f"Starting to monitor {container.name}")
            containers.append(container.name)
            # start the thread
            t.start()
            container_threads.append(t)


# main function
if __name__ == "__main__":
    signal(SIGINT, exit_handler)
    # create a thread to check for new containers
    check_thread = Thread(target=pause_and_check)
    check_thread.start()
    # start the thread
    socketio.run(app, host="0.0.0.0", port=8888)
