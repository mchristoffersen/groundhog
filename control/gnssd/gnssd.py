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
import zmq

import ubx

# dataDir = "/home/radar/groundhog/data/gnss/"
dataDir = "/tmp/"


class GNSS:
    def __init__(self):
        self.redirect = None
        self.redirectID = None
        self.context = None
        self.reSock = None
        self.ptSock = None
        self.logfile = None

        self.connected = False
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
        self.init_gnss_socket()

        while not self.connected:
            logging.info("Initializing GNSS connection")
            self.init_redirect()
            time.sleep(1)

        self.init_messages()

        logging.info("GNSS initialized")

        # Find free filename
        c = 0
        while os.path.isfile(dataDir + "log%d.ubx" % c):
            c += 1

        self.logfile = dataDir + "log%d.ubx" % c

        logging.info("Logging messages to %s" % self.logfile)

        # Initialize socket for serving positon info
        logging.info("Initializing socket for serving GNSS info")
        self.ptSock = self.context.socket(zmq.PUB)
        self.ptSock.bind("tcp://*:5557")

    def __del__(self):
        # Kill redirect
        if self.redirect is not None:
            self.redirect.kill()

        # Kill ZMQ redirect socket
        if self.reSock is not None:
            self.reSock.setsockopt(zmq.LINGER, 0)
            self.reSock.close()

        # Kill PT socket
        if self.ptSock is not None:
            self.reSock.setsockopt(zmq.LINGER, 0)
            self.reSock.close()

        # Kill ZMQ context
        if self.context is not None:
            self.context.destroy()

    def init_gnss_socket(self):
        self.context = zmq.Context()
        self.reSock = self.context.socket(zmq.STREAM)
        self.reSock.bind("tcp://*:5556")

    def send_to_gnss(self, msg):
        if self.reSock is None:
            logging.Error("Redirect socket not initialized, unable to send message")
            return 1

        self.reSock.send_multipart([self.redirectID, msg])
        return 0

    def recv_from_gnss(self):
        if self.reSock is None:
            logging.Error("Redirect socket not initialized, unable to send message")
            return 1

        try:
            _, msg = self.reSock.recv_multipart(flags=zmq.NOBLOCK)
        except zmq.error.Again:
            return None

        # Log message
        if self.logfile is not None:
            with open(self.logfile, mode="ab") as fd:
                fd.write(msg)

        return msg

    def init_redirect(self):
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

        self.redirect = subprocess.Popen(
            [
                "/usr/bin/socat",
                "%s,b115200,raw,echo=0" % dev,
                "TCP:localhost:5556",
            ]
        )

        # Wait for client connection and save ID
        for i in range(10):
            try:
                self.redirectID, msg = self.reSock.recv_multipart(flags=zmq.NOBLOCK)
                self.connected = True
                break
            except zmq.error.Again:
                logging.warning("No socat connection detected, waiting 100ms")
                time.sleep(0.1)

        if self.connected is False:
            logging.error("No socat connection after 1 second")
            return 1

        logging.info("Socat connection detected")

        return 0

    def reset_receiver(self):
        # 20s systemd watchdog will limit this to one reset attempt
        logging.info("Resetting receiver and repeating initialization")
        cmds = ubx.makeReset()
        for cmd in cmds:
            self.send_to_gnss(cmd)
        time.sleep(10)
        self.__init__()
        return 1

    def init_messages(self):
        # Set up gnss to return pvt, rawx, sfrbx, RF
        logging.info("Configuring GNSS messages")

        cmds = ubx.disableAllMessagesCmds()
        for cmd in cmds:
            self.send_to_gnss(cmd)
            time.sleep(0.001)
        time.sleep(1)

        cmds = ubx.enablePVTCmds()
        cmds += ubx.enableRAWXCmds()
        cmds += ubx.enableSFRBXCmds()
        cmds += ubx.enableRFCmds()
        for cmd in cmds:
            self.send_to_gnss(cmd)
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
            msg = self.recv_from_gnss()
            if msg is None:
                continue
            buf += msg
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

    def checkGNSSMessages(self):
        # Read messages from GNSS, parse PVT and RF to update GNSS state
        # then write everything to a file
        msg = self.recv_from_gnss()
        if msg is None:
            return 0

        buf = msg

        while buf != b"":
            while (messageInfo := ubx.getMessage(buf)) != 1:
                (start, end, msgClass, msgID, msg) = messageInfo
                name = ubx.getMsgName(msgClass, msgID)
                buf = buf[end:]
                if name == "UBX-NAV-PVT":
                    pvt = ubx.parseMsg(msg)
                    self.updatePT(pvt)

            msg = self.recv_from_gnss()

            if msg is None and buf == b"":
                return 0
            elif msg is None and buf != b"":
                continue

            buf += msg

    def publishPT(self):
        if self.ptSock is not None:
            self.ptSock.send_pyobj(
                (
                    self.position,
                    self.time,
                    self.fixType,
                    self.timeSinceFix(),
                    time.time(),
                )
            )
        else:
            logging.warning(
                "PT publishing socket does not exist, not sending PT update"
            )

        return 0

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
        gnss.checkGNSSMessages()
        gnss.publishPT()

        if gnss.redirect.poll() is not None:
            logging.warning("socat termiated, attempting to restart GNSS connection")
            del gnss
            gnss = GNSS()
            continue

        time.sleep(0.25)


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
