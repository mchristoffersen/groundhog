import gps
import subprocess
import datetime


def wait_for_fix():
    """Wait for GPS fix"""
    session = gps.gps(mode=gps.WATCH_ENABLE)

    while True:
        report = session.next()
        if report["class"] == "TPV":
            if hasattr(report, "mode") and report.mode >= 2:
                if hasattr(report, "time"):
                    return report.time


def format_filename(gps_time_str):
    """Make filename from time string"""
    dt = datetime.datetime.strptime(gps_time_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    return dt.strftime("%Y%m%dT%H%M%S.ubx")


def record_raw_binary(filename):
    """Dump binary output to a file"""
    with open(filename, "wb", buffering=0) as f:
        proc = subprocess.Popen(["gpspipe", "-R"], stdout=f, bufsize=0)
        try:
            proc.wait()
        except KeyboardInterrupt:
            proc.terminate()


def main():
    gps_time = wait_for_fix()
    filename = format_filename(gps_time)
    record_raw_binary(filename)


if __name__ == "__main__":
    main()
