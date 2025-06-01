import gps
import select
import os
import time
import subprocess
import config
import threading

from flask import Flask, send_file


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
            for i in range(28):  # Try for up to 2.8 seconds
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


@app.route("/api/download")
def download():
    dataDir = "/home/mchristo/proj/groundhog/data/ubx"
    tarPath = "/home/mchristo/proj/groundhog/data/ubx/ubx.tar.gz"

    ubxFiles = [os.path.join(dataDir, f) for f in os.listdir(dataDir)]
    ubxFiles = [f for f in ubxFiles if os.path.isfile(f)]

    # Make tarball
    proc = subprocess.Popen(
        ["tar", "-czvf", tarPath, "--exclude=*.tar.gz", "."],
        cwd=dataDir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    proc.wait()

    return send_file(tarPath, as_attachment=True, download_name="ubx.tar.gz")


if __name__ == "__main__":
    app.run(threaded=False, port=5000)
