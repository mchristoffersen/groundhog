# Re-used input validation routines
import numpy as np

def check_data(data):
    expected_keys = ["rx", "gps", "attrs"]
    missing_keys = []
    for key in expected_keys:
        if key not in data.keys():
            missing_keys.append(keys)

    if len(missing_keys) > 0:
        raise ValueError("Missing expected entries in data: %s" % (missing_keys))

    check_rx(data["rx"])
    check_gps(data["gps"])
    check_attrs(data["attrs"])
    check_rx_gps_match(data["rx"], data["gps"])

def check_gps(gps):
    if type(gps) != np.ndarray:
        raise TypeError("gps is not a numpy ndarray.")

    gpst = [("lon", "<f8"), ("lat", "<f8"), ("hgt", "<f8"), ("utc", "S26")]
    if gps.dtype != gpst:
        raise TypeError(
            "gps has unrecognized datatype.\n\texpected: %s\n\actual: %s"
            % (str(gpst), gps.dtype)
        )


def check_attrs(attrs):
    if type(attrs) != dict:
        raise TypeError("attrs is not a dictionary.")

    expected_keys = ["fs", "pre_trig", "prf", "spt", "stack", "trig"]
    missing_keys = []
    for key in expected_keys:
        if key not in attrs.keys():
            missing_keys.append(keys)

    if len(missing_keys) > 0:
        raise ValueError("Missing expected entries in attrs: %s" % (missing_keys))


def check_rx(rx):
    if type(rx) != np.ndarray:
        raise TypeError("rx is not a numpy ndarray.")

    if len(rx.shape) != 2:
        raise ValueError("rx is not two dimensional.")


def check_rx_gps_match(rx, gps):
    if len(gps) != rx.shape[1]:
        raise ValueError(
            "Number of position/time fixes in gps does not equal number of columns in rx."
        )
