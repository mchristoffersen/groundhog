import flask
import numpy as np
import datetime
import socket
import select
import sys
import pickle
import time

app = flask.Flask(__name__)

# Set up a separate radar state daemon that keeps track of whether radar is running, feedback / messages from radar,
# data from GNSS etc. This daemon is accessed to update the webpage


@app.route("/")
def home():
    return flask.render_template("index.html")


@app.route("/_get_gnss")
def get_gnss():
    try:
        with open("/tmp/gnss_fix", mode="rb") as fd:
            (gnssPosition, gnssTime, fixType, tfix, twrite) = pickle.load(fd)
    except FileNotFoundError:
        return flask.jsonify(fix="no GNSS")

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


if __name__ == "__main__":
    app.run(debug=True)
