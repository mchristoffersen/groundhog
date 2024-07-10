# Normal move out correction
import numpy as np

import ghog.checks
import ghog.constants


def nmo(data, sep, pnmo=3.15):
    """Normal move out and trigger delay correction.

    Args:
        data: Groundhog data dictionary (rx, gps, attrs).
        sep: Separation between source and receiver in meters.
        pnmo: Move out relative permittivity (default = 3.15).

    Returns:
        Dictionary containing the NMO corrected2D data array (rx), numpy structured array with
        per-column positions and times (gps), and data attributes (attrs).
    """
    ghog.checks.check_data(data)

    rx = np.copy(data["rx"])
    attrs = dict(data["attrs"])
    
    if pnmo < 1:
        raise ValueError("vnmo cannot be less than one.")

    if sep < 0:
        raise ValueError("sep cannot be negative.")

    ## Add in trigger delay
    tdelay = sep / ghog.constants.c
    nsamp = np.ceil(tdelay * attrs["fs"]).astype(np.int32)

    rx = np.pad(rx, ((0, nsamp), (0, 0)), mode="constant", constant_values=0)
    rx = np.roll(rx, nsamp, axis=0)
    dt = 1.0 / attrs["fs"]

    # Freq domain makes weird artifacts at end of traces
    cmt = """
    # add zero padding to accomodate time shift plus extra to get rid of edge effects
    epad = nsamp*10
    rx = np.pad(rx, ((nsamp+epad, epad), (0, 0)), mode="constant", constant_values=0)

    # time shift
    RX = np.fft.fft(rx, axis=0)
    w = 2 * np.pi * np.fft.fftfreq(rx.shape[0], d=dt)
    RX = RX * np.exp(-1j * w * tdelay)[:, np.newaxis]
    rx = np.real(np.fft.ifft(RX, axis=0))
    rx = rx[epad:-epad, :]"""

    # trim pre-trigger samples
    rx = rx[attrs["pre_trig"] :, :]
    attrs["spt"] = attrs["spt"] - attrs["pre_trig"] + nsamp
    attrs["pre_trig"] = 0

    ## NMO correction
    vnmo = ghog.constants.c/np.sqrt(pnmo)
    rxnmo = np.zeros_like(rx)
    t0 = np.arange(rx.shape[0]) * dt
    t = np.sqrt(t0**2 + sep**2 / vnmo**2)
    for i in range(rx.shape[1]):
        rxnmo[:, i] = np.interp(t, t0, rx[:, i])

    return {"rx": rxnmo, "gps": np.copy(data["gps"]), "attrs": attrs}
