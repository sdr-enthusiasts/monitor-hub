#!/usr/bin/python3

import eventlet

eventlet.monkey_patch()

import time
from datetime import datetime
import docker
from threading import Thread
from flask_socketio import SocketIO
from flask import Flask, render_template, request, redirect, url_for
from signal import signal, SIGINT
from sys import exit
import os

from sqlalchemy import create_engine, Column, Integer, String, Text, Date, Float
from sqlalchemy.sql import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.declarative import DeclarativeMeta

from sqlalchemy.engine.reflection import Inspector

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
container_classes = []
containers = []

keep_watching = True
container_ready = False

# set up the database

try:
    # get the database path from the environment variable
    db_path = f"sqlite:///{os.getenv('MONITOR_HUB_DATABASE_PATH', default='/run/monitor-hub/monitor-hub.sqlite')}"
    database = create_engine(db_path)
    db_session = sessionmaker(bind=database)
    LogEntries = declarative_base()
except Exception as e:
    print(f"Error setting up database: {e}")
    exit(1)


class Logs(LogEntries):
    __tablename__ = "logs"
    id = Column(Integer, primary_key=True)
    container = Column(String(255), nullable=False)
    time = Column(Float, nullable=False)
    log = Column(Text, nullable=False)


LogEntries.metadata.create_all(database)


def query_to_dict(obj):
    if isinstance(obj.__class__, DeclarativeMeta):
        # an SQLAlchemy class
        fields = {}
        for field in [
            x
            for x in dir(obj)
            if not x.startswith("_")
            and x != "metadata"
            and x is not None
            and x != ""
            and x != "registry"
        ]:
            fields[field] = obj.__getattribute__(field)
        return fields
    return None


class MonitorContainer:
    def __init__(self, name=""):
        self.name = name

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

    def clear_logs(self):
        # clear the logs from the database
        try:
            db = db_session()
            db.query(Logs).filter(Logs.container == self.name).delete()
            db.commit()
            db.close()
        except Exception as e:
            print(f"Error clearing logs: {e}")
        finally:
            containers.remove(self.name)
            # remove container from the list of container classes
            container_classes.remove(self)

    def get_log(self, num_lines=50):
        results = []
        # get the logs from the database
        try:
            session = db_session()
            result = (
                session.query(Logs)
                .where(Logs.container == self.name)
                .order_by(Logs.time.asc())
                .limit(num_lines)
            )

            # convert the result to a list of dictionaries
            results = [query_to_dict(x) for x in result]

            for result in results:
                result.pop("id", None)
        except Exception as e:
            print(f"Error getting logs: {e}")
        finally:
            return results

    def get_log_short(self, num_lines=50):
        # get the logs from the database
        results = self.get_log(num_lines)

        # remove the `container`   key from the dictionary
        for result in results:
            result.pop("container", None)

        return results

    def get_name(self):
        return f"{self.name}"

    # function to monitor a container and append the logs for processing to clients

    def container_logs(self, container):
        global container_ready
        buffered_line = ""
        for line in container.logs(stream=True, timestamps=True):
            try:
                buffered_line = buffered_line + line.decode("utf-8")
                if not buffered_line.endswith("\n"):
                    continue
            except:
                print(format_line(f"Error decoding line: {line}", container.name))
                buffered_line = ""
                continue

            buffered_line = buffered_line.strip()

            try:
                time_stamp, entry = buffered_line.split(" ", 1)
            except Exception as e:
                time_stamp = buffered_line.strip()
                entry = ""

            # grab the time stamp from the log entry
            try:
                # reduce the millisecond precision to 3 digits because python is stupid
                # the milliseconds will look like something like .675967748
                # we want to reduce it to .675. Remove position 22 through 28
                time_stamp = time_stamp[:22] + time_stamp[28:]
                # convert the time stamp to a unix timestamp with milliseconds

                time_stamp = datetime.strptime(
                    time_stamp, "%Y-%m-%dT%H:%M:%S.%f%z"
                ).timestamp()

                # send the log entry to the database
                db = db_session()
                db.add(Logs(container=container.name, time=time_stamp, log=entry))
                db.commit()
                db.close()
                # send the log entry to the client
                if container_ready:
                    socketio.emit(
                        "new_log",
                        {
                            "name": container.name,
                            "time": time_stamp,
                            "log": entry,
                        },
                        namespace="/main",
                    )
            except ValueError as e:
                print(f"Error parsing. Error: {e}, Time: {time_stamp}, Entry: {entry}")
            except Exception as e:
                print(f"Error: {e}")
            finally:
                buffered_line = ""
        # the container has exited so we can remove it from the list
        print("Container {} has exited".format(container.name))
        if container_ready:
            socketio.emit(
                "container_exit",
                {"name": container.name},
                namespace="/main",
            )
        self.clear_logs()


def exit_handler(signal_received, _):
    global keep_watching
    # Handle any cleanup here
    print(f"Exit signal {signal_received} detected. Exiting gracefully")
    keep_watching = False
    exit(0)


# line formatter
def format_line(line, container_name):
    return "{} | {}".format(container_name, line.strip())


def pause_and_check():
    global keep_watching
    while keep_watching:
        check_for_new_containers()
        time.sleep(5)


# function to check for new containers and start monitoring them
def check_for_new_containers():
    global container_ready
    for container in docker.from_env().containers.list():
        if container.name not in containers:
            # create a thread for each container
            c = MonitorContainer(container.name)
            t = Thread(target=c.container_logs, args=(container,))
            print(f"Starting to monitor {container.name}")
            containers.append(container.name)
            print(f"New container: {c.get_name()}")
            if container_ready:
                socketio.emit(
                    "container_start",
                    {
                        "name": c.get_name(),
                    },
                    namespace="/main",
                )
            # start the thread
            t.start()
            container_classes.append(c)
    container_ready = True


# main route
@app.route("/")
def index():
    # only by sending this page first will the client be connected to the socketio instance
    return render_template("index.html")


@socketio.on("connect", namespace="/main")
def main_connect():
    print("Client connected")
    requester = request.sid
    output = {}

    for container in container_classes:
        output[container.name] = {
            "logs": container.get_log_short(),
            "status": "running",
            "name": container.name,
        }

    socketio.emit("connect_data", output, namespace="/main", to=requester)


# main function
if __name__ == "__main__":
    signal(SIGINT, exit_handler)

    print("Clearing database")
    try:
        # make sure database is empty
        db = db_session()
        db.query(Logs).delete()
        db.commit()
        db.close()
    except Exception as e:
        print(f"Error clearing database: {e}")
        # exit
        exit(1)
    print("Database cleared")

    # create a thread to check for new containers
    check_thread = Thread(target=pause_and_check)
    check_thread.start()
    # start the thread
    print("Starting to check for new containers. Application is not ready.")
    while not container_ready:
        time.sleep(1)
    print("Initial Container check is done. Application is ready.")

    socketio.run(app, host="0.0.0.0", port=8888)
