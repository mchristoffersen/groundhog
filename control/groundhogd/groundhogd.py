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

    gui2dae = posix.mkfifo(gui2dae_path)
    dae2gui = posix.mkfifo(dae2gui_path)
    rdr2dae = posix.mkfifo(rdr2dae_path)
    rdr2gui = posix.mkfifo(rdr2gui_path)
    
    # Is the radar running 
    running = False

    while True:
        systemd.daemon.notify("WATCHDOG=1")

        # Check for message from GUI
        with open(gui2dae_path, "r") as pipe:
              msg = pipe.read()
        
        if(msg == "start"):
            # Find new filename
            base = "/home/radar/groundhog/data/"

            for i in range(10000):
                name = base + "groundhog%04d" % i
                if (not os.path.isfile(name + ".ghog")):
                    break
            if(i == 9999):
                logging.error("Out of data file names")
                sys.exit(1)
            

	    radar = subprocess.Popen(
                [
                    "/home/radar/groundhog/control/src/radar",
                    "--file "$filename.ghog" --trigger 10000 --pretrig 8 --spt 512 --stack 256",
                ]
            )

	elif(msg == "stop"):
	    pass
	    # Stop radar
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
