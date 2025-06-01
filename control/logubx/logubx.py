import gps
import subprocess
import datetime
import time
import os
import select


def wait_for_fix():
    """Wait for GPS fix"""
    session = gps.gps(mode=gps.WATCH_ENABLE)

    while True:
        report = session.next()
        if report["class"] == "TPV":
            if hasattr(report, "mode") and report.mode >= 2:
                if hasattr(report, "time"):
                    return report.time


def format_filename(gps_time_str, outDir):
    """Make filename from time string"""
    dt = datetime.datetime.strptime(gps_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    return os.path.join(outDir, dt.strftime("%Y%m%dT%H%M%S.ubx"))


def record_raw_binary(filename):
    """Dump binary output to a file"""
    with open(filename, "wb", buffering=0) as f:
        proc = subprocess.Popen(["gpspipe", "-R"], stdout=f, bufsize=0)
        try:
            time.sleep(0.5)

            ubx = gps.gps(mode=gps.WATCH_ENABLE)
            if select.select([ubx.sock], [], [], 1.5)[0]:
                pass
            else:
                # Quit if no messages for 1.5 seconds
                proc.terminate()
                return

        except KeyboardInterrupt:
            proc.terminate()
            return


def main():
    outDir = "/home/mchristo/proj/groundhog/data/ubx/"
    while True:
        gps_time = wait_for_fix()
        filename = format_filename(gps_time, outDir)
        record_raw_binary(filename)


if __name__ == "__main__":
    main()
