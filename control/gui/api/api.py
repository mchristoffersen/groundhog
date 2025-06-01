import os
import config
import subprocess
import zmq
import numpy as np
import matplotlib.pyplot as plt
import io
import gps
import select
import threading
import time

from flask import Flask, request, jsonify, send_file, Response


# Global variables
radarProcess = None
gnssProcess = None

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

latest_tpv = None
latest_sky = None
report_lock = threading.Lock()
latest_sky_lock = threading.Lock()
ubx = None


def gnss_poller():
    global latest_tpv, latest_sky, report_lock, ubx

    while True:
        try:
            ubx = gps.gps(mode=gps.WATCH_ENABLE)
            break
        except Exception as e:
            time.sleep(1)
            continue

    while True:
        try:
            haveTpv = False
            haveSky = False
            for i in range(28):  # Try for 2.8 seconds
                if select.select([ubx.sock], [], [], 0.1)[0]:
                    report = ubx.next()
                    if report and report["class"] == "TPV":
                        with report_lock:
                            latest_tpv = report
                        haveTpv = True
                    if report and report["class"] == "SKY":
                        if "nSat" in report:
                            with report_lock:
                                latest_sky = report
                            haveSky = True
                    if haveTpv and haveSky:
                        break

            if not haveTpv:
                latest_tpv = None
            if not haveSky:
                latest_sky = None

        except Exception as e:
            time.sleep(1)


app = Flask(__name__)


with app.app_context():
    thread = threading.Thread(target=gnss_poller, daemon=True)
    thread.start()


def generate_filename():
    # Utility function to generate an unused filename
    for i in range(10000):
        name = os.path.join(config.radarDataDir, "groundhog%04d" % i)
        if not os.path.isfile(name + ".ghog") and not os.path.isfile(name + ".txt"):
            return name


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
    global radarProcess

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
        info["prf"] = str(round(float(info["prf"]))) + " Hz"
        info["synclogsize"] = "%.3f MB" % (
            os.path.getsize(info["file"].replace(".ghog", ".txt")) / 1e6
        )

        info["file"] = os.path.basename(info["file"])

    if radarProcess is None:
        info["bgcolor"] = "lightgrey"
    elif radarProcess is not None and msg is not None:
        info["bgcolor"] = "lightgreen"
    else:
        info["bgcolor"] = "red"

    return {
        "file": info.get("file"),
        "ntrc": info.get("ntrace"),
        "prf": info.get("prf"),
        "adc": info.get("adc"),
        "bgcolor": info.get("bgcolor"),
        "synclogsize": info.get("synclogsize"),
    }


@app.route("/api/gnssTable", methods=["GET"])
def gnssTable():
    global latest_tpv, latest_sky, report_lock

    with report_lock:
        tpv = dict(latest_tpv) if latest_tpv else None
        sky = dict(latest_sky) if latest_sky else None

    bgcolor = "lightgrey"

    # Defaults
    reply = {
        "fix": "",
        "date": "",
        "time": "",
        "lon": "",
        "lat": "",
        "hgt": "",
        "sat": "",
        "bgcolor": bgcolor,
        "logfile": "",
        "logsize": "",
        "logbgcolor": bgcolor,
    }

    if tpv is not None:
        fix = tpv.get("mode", 0)
        utc = tpv.get("time", "T")
        lat = tpv.get("lat")
        lon = tpv.get("lon")
        hgt = tpv.get("alt")

        fixD = {0: "no fix", 1: "no fix", 2: "2D fix", 3: "3D fix"}

        if fix == 0 or fix == 1:
            bgcolor = "red"
            logbgcolor = "lightgrey"
        elif fix == 2:
            bgcolor = "yellow"
            logbgcolor = "red"
        elif fix == 3:
            bgcolor = "lightgreen"
            logbgcolor = "red"

        reply["fix"] = fixD[fix]
        reply["date"] = utc.split("T")[0]
        reply["time"] = utc.split("T")[1].replace(".000Z", "")
        reply["lon"] = lon
        reply["lat"] = lat
        reply["hgt"] = hgt
        reply["bgcolor"] = bgcolor

        # Check on log file
        files = [
            os.path.join(config.gnssDataDir, f) for f in os.listdir(config.gnssDataDir)
        ]
        files = [f for f in files if os.path.isfile(f)]
        if len(files) > 0:
            mostRecent = max(files, key=os.path.getmtime)
            mTime = os.path.getmtime(mostRecent)

            # If file modified within last 5 seconds
            if mTime > time.time() - 5:
                reply["logfile"] = os.path.basename(mostRecent)
                reply["logsize"] = "%.3f MB" % (os.path.getsize(mostRecent) / 1e6)
                logbgcolor = "lightgreen"

        reply["logbgcolor"] = logbgcolor

    if sky is not None:
        nsat = sky.get("nSat")
        usat = sky.get("uSat")

        reply["sat"] = "%d/%d" % (usat, nsat)

    return reply


@app.route("/api/start", methods=["POST"])
def start():
    global radarProcess
    global gnssProcess
    data = request.get_json()

    # Validate input from gui?
    file = generate_filename()

    radarCmd = [
        config.radarExe,
        "--file",
        "%s" % (file + ".ghog"),
        "--trigger",
        "%s" % data["tthr"],
        "--pretrig",
        "%s" % data["pts"],
        "--spt",
        "%s" % data["spt"],
        "--stack",
        "%s" % data["stack"],
    ]

    gnssCmd = ["gpspipe", "-d", "-r", "-u", "-o", "%s" % (file + ".txt")]

    if radarProcess is None and gnssProcess is None:
        radarProcess = subprocess.Popen(
            radarCmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        gnssProcess = subprocess.Popen(
            gnssCmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    else:
        return {"reply": "Acquisition already in progress."}

    return {"reply": "Beginning acquisition: %s" % " ".join(radarCmd)}


@app.route("/api/console", methods=["GET"])
def console():
    global radarProcess

    if radarProcess is None:
        return {"reply": ""}

    # Check if radarProcess is still running
    if not check_pid(radarProcess.pid):
        radarProcess = None
        return {"reply": "Acquisition has unexpectedly stopped."}

    os.set_blocking(radarProcess.stdout.fileno(), False)
    os.set_blocking(radarProcess.stderr.fileno(), False)

    # Read output from radarProcess
    lines = []
    for i in range(100):
        # Fetch up to 100 lines
        output = radarProcess.stderr.readline()
        if output == b"":
            break
        else:
            # print(output.decode("utf-8").strip())
            lines.append(output.decode("utf-8").strip())

    # Read output from radarProcess
    for i in range(100):
        # Fetch up to 100 lines
        output = radarProcess.stdout.readline()
        if output == b"":
            break
        else:
            # print(output.decode("utf-8").strip())
            lines.append(output.decode("utf-8").strip())

    return {"reply": "\n".join(lines)}


@app.route("/api/stop", methods=["POST"])
def stop():
    global radarProcess
    global gnssProcess

    msg = ""

    if radarProcess is None and gnssProcess is None:
        return {"reply": "No acquisition in progress."}

    if radarProcess is not None:
        if check_pid(radarProcess.pid):
            radarProcess.terminate()
            radarProcess.wait()
        else:
            msg += " Radar process unexpectedly dead"
        radarProcess = None
    else:
        msg += " Radar PID unexpectedly missing."

    if gnssProcess is not None:
        if check_pid(gnssProcess.pid):
            gnssProcess.terminate()
            gnssProcess.wait()
        else:
            msg += " GNSS process unexpectly dead."
        gnssProcess = None
    else:
        msg += " GNSS PID unexpectly missing."

    return {"reply": "Stopped acquisition." + msg}


if __name__ == "__main__":
    app.run(threaded=False, port=5000)
