import gps
import subprocess
import datetime
import time
import os
import select


def wait_for_fix():
    # Wait for fix
    session = gps.gps(mode=gps.WATCH_ENABLE)

    while True:
        report = session.next()
        if report["class"] == "TPV":
            if hasattr(report, "mode") and report.mode >= 2:
                if hasattr(report, "time"):
                    return report.time


def make_filename(gps_time_str, outDir):
    # Make filename from time string
    dt = datetime.datetime.strptime(gps_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    return os.path.join(outDir, dt.strftime("%Y%m%dT%H%M%S.ubx"))


def record_raw_binary(filename):
    """Dump raw output to a file"""
    with open(filename, "wb", buffering=0) as f:
        proc = subprocess.Popen(["gpspipe", "-R"], stdout=f, bufsize=0)
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            return


def main():
    outDir = "/home/mchristo/proj/groundhog/data/ubx/"
    while True:
        gps_time = wait_for_fix()
        filename = make_filename(gps_time, outDir)
        record_raw_binary(filename)


if __name__ == "__main__":
    main()
