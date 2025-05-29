import os
import config
import subprocess
import zmq
import numpy as np
import matplotlib.pyplot as plt
import io
import gps
import select
import time

from flask import Flask, request, jsonify, send_file, Response


app = Flask(__name__)


# Global variables
process = None

context = zmq.Context()
radarSock = context.socket(zmq.SUB)
radarSock.setsockopt_string(zmq.SUBSCRIBE, "radar")
radarSock.setsockopt(zmq.RCVTIMEO, 100)
radarSock.connect("tcp://localhost:5557")

traceSock = context.socket(zmq.SUB)
traceSock.setsockopt_string(zmq.SUBSCRIBE, "trace")
traceSock.setsockopt(zmq.RCVTIMEO, 100)
traceSock.connect("tcp://localhost:5557")

poller = zmq.Poller()
poller.register(radarSock, zmq.POLLIN)
poller.register(traceSock, zmq.POLLIN)

ubx = gps.gps(mode=gps.WATCH_ENABLE)


def generate_filename():
    # Utility function to generate an unused filename
    for i in range(10000):
        name = os.path.join(config.dataDir, "groundhog%04d" % i)
        if not os.path.isfile(name + ".ghog"):
            return name + ".ghog"
            break


def check_pid(pid):
    # Check if PID exists
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True


@app.route("/api/trace", methods=["GET"])
def trace():
    # Check ZeroMQ messages
    global traceSock
    global poller
    global process

    msg = None
    reply = {"x": [], "t": []}
    while traceSock in dict(poller.poll(timeout=0)):
        msg = traceSock.recv()

    if msg is not None:
        trace = np.frombuffer(msg[5:], dtype=np.int64)

        # Plot with python
        fig, ax = plt.subplots(figsize=(2, 4))
        ax.plot(trace, np.arange(len(trace)), "k-")
        ax.spines[["bottom", "right"]].set_visible(False)
        ax.tick_params(top=True, labeltop=True, bottom=False, labelbottom=False)
        ax.set_ylim(len(trace), 0)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return send_file(buf, mimetype="image/png")

    else:
        return Response(status=204)

        # Plot with JS
        # reply["x"] = trace.tolist()
        # reply["t"] = np.arange(len(trace)).tolist()

    # return jsonify(reply)


@app.route("/api/radarTable", methods=["GET"])
def radarTable():
    # Check ZeroMQ messages
    global radarSock
    global poller
    global process

    msg = None
    info = {}

    # Get most recent message
    while radarSock in dict(poller.poll(timeout=0)):
        msg = radarSock.recv_string()

    if msg is not None:
        pairs = msg.split(",")

        for pair in pairs:
            k, v = pair.split("=")
            info[k] = v

        info["adc"] = str(float(info["adc"]) / 1e6) + " MHz"
        info["prf"] += " Hz"
    else:
        info["ntrace"] = ""
        info["prf"] = ""
        info["adc"] = ""

    if process is None:
        info["bgcolor"] = "lightgrey"
    elif process is not None and msg is not None:
        info["bgcolor"] = "lightgreen"
    else:
        info["bgcolor"] = "red"

    return {
        "ntrc": info["ntrace"],
        "prf": info["prf"],
        "adc": info["adc"],
        "bgcolor": info["bgcolor"],
    }


@app.route("/api/gnssTable", methods=["GET"])
def gnssTable():
    # TODO: some sort of timeout here...
    latest_tpv = None
    for i in range(18):  # Try for a bit more than a second
        if select.select([ubx.sock], [], [], 0.1)[0]:
            report = ubx.next()
            if report and report["class"] == "TPV":
                latest_tpv = report
                break

    bgcolor = "lightgrey"

    if latest_tpv is not None:
        fix = getattr(latest_tpv, "mode", 0)
        utc = getattr(latest_tpv, "time", "T")
        lat = getattr(latest_tpv, "lat", None)
        lon = getattr(latest_tpv, "lon", None)
        hgt = getattr(latest_tpv, "alt", None)

        fixD = {0: "no fix", 1: "no fix", 2: "2D fix", 3: "3D fix"}

        if fix == 0 or fix == 1:
            bgcolor = "red"
        elif fix == 2:
            bgcolor = "yellow"
        elif fix == 3:
            bgcolor = "lightgreen"

        return {
            "fix": fixD[fix],
            "date": utc.split("T")[0],
            "time": utc.split("T")[1],
            "lon": lon,
            "lat": lat,
            "hgt": hgt,
            "bgcolor": bgcolor,
        }
    return {
        "fix": "",
        "date": "",
        "time": "",
        "lon": "",
        "lat": "",
        "hgt": "",
        "bgcolor": bgcolor,
    }


@app.route("/api/start", methods=["POST"])
def start():
    global process
    data = request.get_json()

    # Validate input from gui?

    cmd = [
        config.radarExe,
        "--file",
        "%s" % generate_filename(),
        "--trigger",
        "%s" % data["tthr"],
        "--pretrig",
        "%s" % data["pts"],
        "--spt",
        "%s" % data["spt"],
        "--stack",
        "%s" % data["stack"],
    ]

    if process is None:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    else:
        return {"reply": "Acquisition already in progress."}

    return {"reply": "Beginning acquisition: %s" % " ".join(cmd)}


@app.route("/api/console", methods=["GET"])
def console():
    global process

    if process is None:
        return {"reply": ""}

    # Check if process is still running
    if not check_pid(process.pid):
        process = None
        return {"reply": "Acquisition has unexpectedly stopped."}

    os.set_blocking(process.stdout.fileno(), False)
    os.set_blocking(process.stderr.fileno(), False)

    # Read output from process
    lines = []
    for i in range(100):
        # Fetch up to 100 lines
        output = process.stderr.readline()
        if output == b"":
            break
        else:
            # print(output.decode("utf-8").strip())
            lines.append(output.decode("utf-8").strip())

    # Read output from process
    for i in range(100):
        # Fetch up to 100 lines
        output = process.stdout.readline()
        if output == b"":
            break
        else:
            # print(output.decode("utf-8").strip())
            lines.append(output.decode("utf-8").strip())

    return {"reply": "\n".join(lines)}


@app.route("/api/stop", methods=["POST"])
def stop():
    global process
    if process is None:
        return {"reply": "No acquisition in progress."}

    print("Checking if process is still running", check_pid(process.pid))
    if not check_pid(process.pid):
        process = None
        return {"reply": "Acquisition has unexpectedly stopped."}

    # Terminate process
    process.terminate()
    process.wait()

    process = None

    return {"reply": "Stopped acquisition."}


if __name__ == "__main__":
    app.run(threaded=False, port=5000)
