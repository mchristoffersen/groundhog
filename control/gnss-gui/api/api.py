import gps
import select
import os
import time
import subprocess

from flask import Flask, send_file


app = Flask(__name__)


# Global variables


@app.route("/api/gnssTable", methods=["GET"])
def gnssTable():
    ubx = gps.gps(mode=gps.WATCH_ENABLE)
    dataDir = "/home/mchristo/proj/groundhog/data/ubx"

    latest_tpv = None
    latest_sky = None
    haveSky = False
    haveTpv = False
    for i in range(45):  # Try for a bit more than four seconds
        if select.select([ubx.sock], [], [], 0.1)[0]:
            report = ubx.next()
            if report and report["class"] == "TPV":
                latest_tpv = report
                haveTpv = True
            if report and report["class"] == "SKY":
                if "nSat" in report:
                    latest_sky = report
                    haveSky = True
        if haveSky and haveTpv:
            break

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

    if latest_tpv is not None:
        fix = getattr(latest_tpv, "mode", 0)
        utc = getattr(latest_tpv, "time", "T")
        lat = getattr(latest_tpv, "lat", None)
        lon = getattr(latest_tpv, "lon", None)
        hgt = getattr(latest_tpv, "alt", None)

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
        files = [os.path.join(dataDir, f) for f in os.listdir(dataDir)]
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

    if latest_sky is not None:
        nsat = getattr(latest_sky, "nSat")
        usat = getattr(latest_sky, "uSat")

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
