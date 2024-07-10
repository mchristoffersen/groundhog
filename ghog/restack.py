# Restack traces to constant distance intervals
import numpy as np
import pyproj

import ghog.checks


def restack(data, interval, dcut=0):
    """Restack traces to constant distance intervals.

    Args:
        data: Groundhog data dictionary (rx, gps, attrs).
        interval: Constant distance interval to restack rx to. Must be greater than
            all original distance intervals in rx (this function does not interpolate).
        dcut: Cutoff threshold for no motion between two traces. Distances below this threshold
            are set to zero for the purpose of restacking. Helpful for noisy position data (default = 0).

    Returns:
        Dictionary containing the restacked 2D data array (rx), numpy structured array with per-column
        positions and times (gps), and data attributes (attrs).
    """
    ghog.checks.check_data(data)

    rx = data["rx"]
    gps = data["gps"]
    attrs = dict(data["attrs"])

    if interval <= 0:
        raise ValueError("interval cannot be zero or negative.")

    if dcut < 0:
        raise ValueError("dcut cannot be negative.")

    xform = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:4978")
    x, y, z = xform.transform(gps["lat"], gps["lon"], gps["hgt"])
    steps = np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2 + np.diff(z) ** 2)
    steps[steps < dcut] = 0
    dist = np.append(
        0,
        np.cumsum(steps),
    )

    if np.any(steps > interval):
        raise ValueError(
            "Restacking interval is not greater than all distance steps in raw dataset.\n\trestacking interval: %.3f\n\tmax raw interval: %.3f"
            % (interval, np.max(steps))
        )

    nrstk = np.ceil(dist[-1] / interval).astype(np.uint32)

    rx_rstk = np.zeros((rx.shape[0], nrstk), dtype=np.float64)
    gps_rstk = np.empty(nrstk, gps.dtype)

    time = np.array(list(map(np.datetime64, gps["utc"])))
    epoch = time[0]
    time_sse = time - epoch

    for i in range(nrstk):
        mask = np.logical_and(dist >= interval * i, dist < interval * (i + 1))
        rx_rstk[:, i] = np.mean(rx[:, mask], axis=1)
        gps_rstk[i] = (
            np.mean(gps["lon"][mask]),
            np.mean(gps["lat"][mask]),
            np.mean(gps["hgt"][mask]),
            np.datetime_as_string(epoch + np.mean(time_sse[mask])),
        )

    attrs["stack_interval"] = interval

    return {"rx": rx_rstk, "gps": gps_rstk, "attrs": attrs}
