import flask
import numpy as np
import datetime
import socket
import select
import sys
import pickle
import time

import zmq

app = flask.Flask(__name__)

# Set up a separate radar state daemon that keeps track of whether radar is running, feedback / messages from radar,
# data from GNSS etc. This daemon is accessed to update the webpage


def send2dae(msg):
    context = zmq.Context()
    daeSock = context.socket(zmq.REQ)
    daeSock.setsockopt(zmq.RCVTIMEO, 1200)
    daeSock.connect("tcp://localhost:5555")

    daeSock.send_string(msg)

    try:
        msg = daeSock.recv().decode()
    except zmq.error.Again:
        msg = 'Message failed. No reply received from daemon.  -  "' + msg + '"'

    daeSock.setsockopt(zmq.LINGER, 0)
    daeSock.close()
    context.destroy()
    return msg


@app.route("/")
def home():
    return flask.render_template("index.html")


@app.route("/_get_gnss")
def get_gnss():
    context = zmq.Context()
    gnssSock = context.socket(zmq.SUB)
    gnssSock.setsockopt_string(zmq.SUBSCRIBE, "")
    gnssSock.setsockopt(zmq.RCVTIMEO, 500)
    gnssSock.connect("tcp://localhost:5557")

    try:
        msg = gnssSock.recv_pyobj()
    except zmq.error.Again:
        msg = None

    gnssSock.setsockopt(zmq.LINGER, 0)
    gnssSock.close()
    context.destroy()

    if msg is None:
        return flask.jsonify(fix="No GNSS")

    (gnssPosition, gnssTime, fixType, tfix, twrite) = msg

    twrite = time.time() - twrite
    strDate = "%04d-%02d-%02d" % (gnssTime["year"], gnssTime["month"], gnssTime["day"])
    strTime = "%02d:%02d:%02d" % (gnssTime["hour"], gnssTime["min"], gnssTime["sec"])
    return flask.jsonify(
        fix=fixType,
        date=strDate,
        time=strTime,
        lon="%.5f" % gnssPosition["lon"],
        lat="%.5f" % gnssPosition["lat"],
        hgt="%.3f" % gnssPosition["hgt"],
        tfix=tfix,
        twrite=twrite,
    )


@app.route("/_get_radar")
def get_radar():
    return flask.jsonify(ntrc="69", nbuf="420", prf="2000", adc="25e6")


@app.route("/_start", methods=["POST"])
def start():
    data = flask.request.data
    msg = "start" + data.decode()
    resp = send2dae(msg)
    return flask.jsonify(text=resp)


@app.route("/_stop", methods=["POST"])
def stop():
    msg = "stop"
    resp = send2dae(msg)
    return flask.jsonify(text=resp)


@app.route("/_get_console")
def get_console():
    with open("/tmp/dae2gui", mode="r") as dae2gui:
        msg = dae2gui.readline()
        print("msg " + msg, file=sys.stdout)
    return flask.jsonify(msg=msg)


if __name__ == "__main__":
    app.run(debug=True)
