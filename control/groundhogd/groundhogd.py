#!/home/radar/groundhog/ghogenv/bin/python

# Groundhog Daemon
# Manages GPS and radar

# Skeleton from here:
# https://www.loggly.com/blog/new-style-daemons-python/

import logging
import sys
import time
import os
import posix
import socket
import select
import subprocess
import json

import systemd.daemon
import numpy as np


def main():
    root_logger = logging.getLogger()
    root_logger.setLevel("INFO")
    root_logger.addHandler(SystemdHandler())
    logging.info("Starting groundhogd")

    # set up named pipes
    logging.info("Setting up named pipes")
    gui2dae_path = "/tmp/gui2dae"
    dae2gui_path = "/tmp/dae2gui"
    rdr2dae_path = "/tmp/rdr2dae"
    rdr2gui_path = "/tmp/rdr2gui"

    for path in [gui2dae_path, dae2gui_path, rdr2dae_path, rdr2gui_path]:
        try:
            os.unlink(path)
        except OSError:
            if os.path.exists(path):
                logging.error("Failed to delete fifo path: %s" % path)
                sys.exit(1)
        os.mkfifo(path)

    # Is the radar running
    running = False

    # Open 2dae pipes for reading
    gui2dae_fd = os.open(gui2dae_path, os.O_RDONLY | os.O_NONBLOCK)
    gui2dae = os.fdopen(gui2dae_fd)

    # Open 2gui pipe for writing
    # dae2gui = open(dae2gui_path, mode="w")
    dae2gui = None

    while True:
        systemd.daemon.notify("WATCHDOG=1")

        # Check for message from GUI
        msg = gui2dae.readline()
        print(msg)

        if "start" in msg and not running:
            if(dae2gui is None):
            # Make command from json
            params = json.loads(msg.replace("start", ""))

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
                logging.error("Out of data file names")
                sys.exit(1)

            args = "--file %s --trigger %s --pretrig %s --spt %s --stack %s" % (
                name,
                params["trigger"],
                params["pretrig"],
                params["spt"],
                params["stack"],
            )

            exe = "/home/radar/groundhog/control/src/radar"

            dae2gui.write(cmd + " " + exe)

            try:
                radar = subprocess.Popen([exe, args])
            except FileNotFoundError:
                dae2gui.write(
                    "Failed to start radar - could not locate executable %s" % exe
                )
                logging.error(
                    "Failed to start radar - could not locate executable %s" % exe
                )
            running = True
        elif "start" in msg and running:
            dae2gui.write("Ignoring start command while radar is running.\n")
            logging.info("Ignoring start command while radar is running.")
        elif "stop" in msg and running:
            dae2gui.write("Stopping radar")
            logging.info("Stopping radar.")
            radar.kill()
        elif "stop" in msg and not running:
            dae2gui.write("Ignoring stop command while radar is not running\n")
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
