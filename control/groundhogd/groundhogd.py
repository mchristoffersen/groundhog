#!/home/radar/groundhog/ghogenv/bin/python

# Groundhog Daemon
# Manages GPS and radar

# Skeleton from here:
# https://www.loggly.com/blog/new-style-daemons-python/

import logging
import sys
import time
import os
import subprocess
import json

import systemd.daemon
import numpy as np
import zmq

# Radar executable
# exe = "/home/radar/groundhog/control/src/radar"
exe = "/usr/bin/ls"


def main():
    root_logger = logging.getLogger()
    root_logger.setLevel("INFO")
    root_logger.addHandler(SystemdHandler())
    logging.info("Starting groundhogd")

    # set up sockets
    context = zmq.Context()
    guiSock = context.socket(zmq.REP)
    guiSock.bind("tcp://*:5555")

    # gnssSock = context.socket(zmq.SUB)
    # gnssSock.bind("tcp://*:5556")

    # Is the radar running
    running = False

    while True:
        systemd.daemon.notify("WATCHDOG=1")

        # Check for message from GUI
        try:
            guiMsg = guiSock.recv(flags=zmq.NOBLOCK).decode()
        except zmq.error.Again:
            guiMsg = ""
            pass

        if "start" in guiMsg and not running:
            # Make command from message
            params = json.loads(guiMsg.replace("start", ""))

            # Strip any non-digits from strings
            for k, v in params.items():
                params[k] = "".join(c for c in v if c.isdigit())

            # Find new filename
            base = "/home/radar/groundhog/data/"

            for i in range(10000):
                name = base + "groundhog%04d.ghog" % i
                if not os.path.isfile(name):
                    break
            if i == 9999:
                guiReply += (
                    "\n" + "!!! Failed to start radar - out of data file names !!!"
                )
                logging.error("Out of data file names")
                guiSock.send_string(guiReply)
                guiMsg = ""
                continue

            args = "--file %s --trigger %s --pretrig %s --spt %s --stack %s" % (
                name,
                params["trigger"],
                params["pretrig"],
                params["spt"],
                params["stack"],
            )

            guiReply = exe + " " + args
            guiMsg = ""

            try:
                radar = subprocess.Popen([exe, args])
                time.sleep(0.25)
                print(radar.returncode)
            except FileNotFoundError:
                guiReply += (
                    "\n"
                    + "!!! Failed to start radar - could not locate executable %s !!!"
                    % exe
                )

                logging.error(
                    "Failed to start radar - could not locate executable %s" % exe
                )
                guiSock.send_string(guiReply)
                guiMsg = ""
                continue

            guiReply += "\n" + "Data file  -  %s" % name

            running = True
            guiSock.send_string(guiReply)
            guiMsg = ""

        elif "start" in guiMsg and running:
            guiSock.send_string("Ignoring start command while radar is running.")
            guiMsg = ""
            logging.info("Ignoring start command while radar is running.")
        elif "stop" in guiMsg and running:
            guiSock.send_string("Stopping radar.\n")
            guiMsg = ""
            logging.info("Stopping radar.")
            radar.kill()
            running = False
        elif "stop" in guiMsg and not running:
            guiSock.send_string("Ignoring stop command while radar is not running.")
            guiMsg = ""
            logging.info("Ignoring stop command while radar is not running.")
        time.sleep(1)


class SystemdHandler(logging.Handler):
    # https://0pointer.de/public/systemd-man/sd-daemon.html
    PREFIX = {
        # EMERG <0>
        # ALERT <1>
        logging.CRITICAL: "<2>",
        logging.ERROR: "<3>",
        logging.WARNING: "<4>",
        # NOTICE <5>
        logging.INFO: "<6>",
        logging.DEBUG: "<7>",
        logging.NOTSET: "<7>",
    }

    def __init__(self, stream=sys.stdout):
        self.stream = stream
        logging.Handler.__init__(self)

    def emit(self, record):
        try:
            msg = self.PREFIX[record.levelno] + self.format(record)
            msg = msg.replace("\n", "\\n")
            self.stream.write(msg + "\n")
            self.stream.flush()
        except Exception:
            self.handleError(record)


main()
