#!/usr/bin/env python3

# Groundhog Daemon
# Manages GPS and radar

# Skeleton from here:
# https://www.loggly.com/blog/new-style-daemons-python/

import logging
import sys
import time
import os
import socket
import select
import subprocess

import systemd.daemon
import serial.tools.list_ports

import ubx
import ubx.ubx

class GNSS():
    def __init__(self):
        self.connected = False
        self.initialized = False
        self.logger = logging.getLogger()
        
        logging.info("Initializing GNSS instance")
        self.init_socket()

        self.attempt_connection()

        self.dump_connection()

        #if(self.attempt_connection() == 0):
        #    self.set_messages()

    def init_socket(self):
        # Set up UNIX domain socket server-side
        logging.info("Configuring GNSS unix socket")
        # Set the path for the Unix socket
        self.socket_path = socket_path = "/tmp/gps"

        # remove the socket file if it already exists
        try:
            os.unlink(socket_path)
        except OSError:
            if os.path.exists(socket_path):
                raise RuntimeError("Failed to delete socket path")

        # Create the Unix socket server
        self.server = server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(socket_path)
        server.listen(1)

        return 0

    def attempt_connection(self):
        logging.info("Searching for ZED-F9P GNSS")
        desc = "u-blox GNSS receiver"
        dev = None

        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.description == desc:
                dev = port.device
                break

        if(dev is None):
            logging.info("Did not find ZED-F9P GNSS")
            return 1

        logging.info("Found ZED-F9P GNSS")
        logging.info("Starting socat redirect")
        self.socat = subprocess.Popen(["/usr/bin/socat", "%s,b115200,raw,echo=0" % dev, "UNIX-CONNECT:%s" % self.socket_path])
        self.connected = True
        return 0

    def dump_connection(self):
        logging.info("Dumping GNSS stream")
        try:
            while True:
                while True:
                    logging.info("Waiting for connection")
                    # Wait for client connection
                    ready = select.select([self.server], [], [], 1)[0]
                    if len(ready) > 0:
                        connection, _ = self.server.accept()
                        #cmds = ubx.ubx.disableAllMessagesCmds()
                        cmds = ubx.ubx.enablePVTCmds()
                        for cmd in cmds:
                            connection.sendall(cmd)
                        break
                while True:
                    msg = connection.recv(65536)
                    if(msg == b""):
                        connection.close()
                        break
                    print(msg)
        except KeyboardInterrupt:
            pass

    def set_messages(self):
        logging.info("Setting ZED-F9P messages")
        self.gnss.disableAllMessages()
        self.gnss.enablePVT()
        self.gnss.enableRF()
        self.gnss.enableRAWX()
        self.gnss.enableSFRBX()
        logging.info("ZED-F9P messages set")

    def check_messages(self):
        logging.info("Checking ZED-F9P messages")
        expected_messages = [
            "UBX-NAV-PVT",
            "UBX-MON-RF",
            "UBX-RXM-RAWX",
            "UBX-RXM-SFRBX"
        ]
        t0 = time.time()



        

def main():
    root_logger = logging.getLogger()
    root_logger.setLevel("INFO")
    root_logger.addHandler(SystemdHandler())
    logging.info("Starting groundhogd")

    while True:
        systemd.daemon.notify("WATCHDOG=1")
        gnss = GNSS()
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