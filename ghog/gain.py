import numpy as np

import ghog.checks


def gain(data, tpow=1):
    """Apply gain to traces.

    Args:
        data: Groundhog data dictionary (rx, gps, attrs).
        tpow: Power of time gain to apply to each trace (default = 1 : linear gain).

    Returns:
        Dictionary containing the gained 2D data array (rx), numpy structured array with
        per-column positions and times (gps), and data attributes (attrs).
    """

    rx = np.copy(data["rx"])
    attrs = data["attrs"]

    t = (np.arange(rx.shape[0]) - attrs["pre_trig"]) / attrs["fs"]
    gain = t**tpow
    gain = gain / np.max(gain)
    rxgain = rx * gain[:, np.newaxis]

    return {"rx": rxgain, "gps": np.copy(data["gps"]), "attrs": attrs}
