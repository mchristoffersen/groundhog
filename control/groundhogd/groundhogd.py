#!/usr/bin/env python3

# https://www.loggly.com/blog/new-style-daemons-python/

import logging
import sys
import time
import systemd.daemon

def main():
    root_logger = logging.getLogger()
    root_logger.setLevel("INFO")
    root_logger.addHandler(SystemdHandler())

    while True:
        #logging.debug("Debug")
        logging.info("Hello peagret")
        #logging.warning("Warning")
        systemd.daemon.notify("WATCHDOG=1")
        time.sleep(9)

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
        logging.NOTSET: "<7>"
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