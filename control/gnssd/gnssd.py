#!/home/radar/groundhog/ghogenv/bin/python

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
import pickle

import systemd.daemon
import serial.tools.list_ports
import numpy as np

import ubx


class GNSS:
    def __init__(self):
        self.socat = None
        self.server = None

        self.connected = False
        self.initialized = False
        self.logger = logging.getLogger()

        # PT state
        self.position = {"lat": 0, "lon": 0, "hgt": 0}
        self.time = {
            "year": 0,
            "month": 0,
            "day": 0,
            "hour": 0,
            "min": 0,
            "sec": 0,
        }
        self.fixType = "no fix"
        self.lastFix = None  # fix time

        logging.info("Initializing GNSS instance")
        self.init_socket()

        while not self.connected:
            logging.info("Initializing GNSS connection")
            self.init_connection()
            time.sleep(1)

        self.init_messages()

        logging.info("GNSS initialized")

        # Find free filename
        dataDir = "/home/radar/groundhog/data/gnss/"
        c = 0
        while os.path.isfile(dataDir + "log%d.ubx" % c):
            c += 1

        self.logfile = dataDir + "log%d.ubx" % c

        logging.info("Logging messages to %s" % self.logfile)

    def __del__(self):
        # Kill socat
        if self.socat is not None:
            self.socat.kill()

        # Shut down socket
        if self.server is not None:
            self.server.shutdown(socket.SHUT_RDWR)
            self.server.close()

    def init_socket(self):
        # Set up UNIX domain socket server-side
        logging.info("Configuring GNSS unix socket")
        # Set the path for the Unix socket
        self.socket_path = socket_path = "/tmp/gnss"

        # remove the socket file if it already exists
        try:
            os.unlink(socket_path)
        except OSError:
            if os.path.exists(socket_path):
                logging.error("Failed to delete socket path: %s" % socket_path)
                sys.exit(1)

        # Create the Unix socket server
        self.server = server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(socket_path)
        server.listen(1)

        return 0

    def init_connection(self):
        # Set up ZED-F9P connection (socat to redirect serial data to socket)
        logging.info("Searching for ZED-F9P GNSS")
        desc = "u-blox GNSS receiver"
        dev = None

        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.description == desc:
                dev = port.device
                break

        if dev is None:
            logging.info("Did not find ZED-F9P GNSS in serial devices")
            return 1

        logging.info("Found ZED-F9P GNSS")
        logging.info("Starting socat redirect")

        self.socat = subprocess.Popen(
            [
                "/usr/bin/socat",
                "%s,b115200,raw,echo=0" % dev,
                "UNIX-CONNECT:%s" % self.socket_path,
            ]
        )

        # Wait for client connection
        while not self.connected:
            logging.info("Looking for socat connection")
            ready = select.select([self.server], [], [], 1)[0]
            if len(ready) > 0:
                self.connection, _ = self.server.accept()
                self.connection.settimeout(0.1)
                self.connected = True
            if self.socat.returncode is not None:
                logging.warning("socat terminated")
                return 1

        return 0

    def reset_receiver(self):
        # 20s systemd watchdog will limit this to one reset attempt
        logging.info("Resetting receiver and repeating initialization")
        cmds = ubx.makeReset()
        for cmd in cmds:
            self.connection.sendall(cmd)
        time.sleep(10)
        self.__init__()
        return 1

    def init_messages(self):
        # Set up gnss to return pvt, rawx, sfrbx, RF
        logging.info("Configuring GNSS messages")

        cmds = ubx.disableAllMessagesCmds()
        for cmd in cmds:
            self.connection.sendall(cmd)
            time.sleep(0.001)
        time.sleep(1)

        cmds = ubx.enablePVTCmds()
        cmds += ubx.enableRAWXCmds()
        cmds += ubx.enableSFRBXCmds()
        cmds += ubx.enableRFCmds()
        for cmd in cmds:
            self.connection.sendall(cmd)
            time.sleep(0.001)

        logging.info("Checking that message initialization was sucessful")
        expected_messages = [
            "UBX-NAV-PVT",
            "UBX-RXM-RAWX",
            "UBX-RXM-SFRBX",
            "UBX-MON-RF",
        ]

        t0 = time.time()
        buf = b""
        while np.abs(t0 - time.time()) < 5:
            try:
                buf += self.connection.recv(65536)
            except TimeoutError:
                time.sleep(1)
                continue
            while (messageInfo := ubx.getMessage(buf)) != 1:
                (start, end, msgClass, msgID, msg) = messageInfo
                name = ubx.getMsgName(msgClass, msgID)
                buf = buf[end:]
                if name in expected_messages:
                    expected_messages.remove(name)
            if len(expected_messages) == 0:
                break
        if len(expected_messages) != 0:
            logging.warning(
                "Did not detect following GNSS messages %s" % expected_messages
            )
            self.reset_receiver()
            return 1
        return 0

    def checkMessages(self, save=False):
        # Read messages from GNSS, parse PVT and RF to update GNSS state
        # then write everything to a file
        try:
            buf = self.connection.recv(65536)
        except TimeoutError:
            return 0

        with open(self.logfile, mode="ab") as fd:
            fd.write(buf)

        while buf != b"":
            while (messageInfo := ubx.getMessage(buf)) != 1:
                (start, end, msgClass, msgID, msg) = messageInfo
                name = ubx.getMsgName(msgClass, msgID)
                buf = buf[end:]
                if name == "UBX-NAV-PVT":
                    pvt = ubx.parseMsg(msg)
                    self.updatePT(pvt)
            try:
                new = self.connection.recv(65536)
            except TimeoutError:
                return 0

            with open(self.logfile, mode="ab") as fd:
                fd.write(new)

            buf += new

    def updatePT(self, pvt):
        # Update state from PVT message
        typeDict = {
            0: "no fix",
            1: "DR",
            2: "2D fix",
            3: "3D fix",
            4: "GNSS + DR",
            5: "time only",
        }

        # TODO: should be checking time validity/gnss flags here
        self.time["year"] = pvt["year"]
        self.time["month"] = pvt["month"]
        self.time["day"] = pvt["day"]
        self.time["hour"] = pvt["hour"]
        self.time["min"] = pvt["min"]
        self.time["sec"] = float(pvt["sec"]) + (float(pvt["nano"]) / 1e9)
        self.position["lon"] = float(pvt["lon"]) * 1e-7
        self.position["lat"] = float(pvt["lat"]) * 1e-7
        self.position["hgt"] = float(pvt["height"]) * 1e-3  # convert mm to m
        self.lastFix = time.time()
        self.fixType = typeDict[pvt["fixType"]]

    def picklePT(self):
        return pickle.dumps(
            (self.position, self.time, self.fixType, self.timeSinceFix(), time.time())
        )

    def timeSinceFix(self):
        if self.lastFix is not None:
            return time.time() - self.lastFix
        else:
            return -1

    def timeString(self):
        strDate = "%04d-%02d-%02d" % (
            self.time["year"],
            self.time["month"],
            self.time["day"],
        )
        strTime = "%02d:%02d:%.9f" % (
            self.time["hour"],
            self.time["min"],
            self.time["sec"],
        )
        return strDate + "T" + strTime


def main():
    root_logger = logging.getLogger()
    root_logger.setLevel("INFO")
    root_logger.addHandler(SystemdHandler())
    logging.info("Starting gnssd")

    gnss = GNSS()

    while True:
        systemd.daemon.notify("WATCHDOG=1")
        gnss.checkMessages()

        # Write current fix
        with open("/tmp/gnss_fix", mode="wb") as fd:
            fd.write(gnss.picklePT())

        # Write time as text
        with open("/tmp/gnss_time", mode="w") as fd:
            fd.write("%s,%f" % (gnss.timeString(), gnss.timeSinceFix()))

        if gnss.socat.poll() is not None:
            logging.warning("socat termiated, attempting to restart GNSS connection")
            gnss = GNSS()
            continue

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
