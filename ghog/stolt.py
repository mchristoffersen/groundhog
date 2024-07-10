# Stolt migration
import numpy as np
import scipy.signal

import ghog.checks


def stolt(data, pmig=3.15, ntaper=32, px=None, pt=None):
    """Perform Stolt migration.

    This function performs Stolt migration.

    Args:
        data: Groundhog data dictionary (rx, gps, attrs).
        pmig: Migration relative permittivity (default = 3.15).
        ntaper: Taper width in pixels, applied to all sides of image (default = 32).
        pt: Zero padding along time axis (default = 10x length of time axis).
        px: Zero padding along distance axis (default = 1x length of distance axis).

    Returns:
        Dictionary containing the migrated 2D data array (rx), numpy structured array with per-column
        positions and times (gps), and data attributes (attrs)
    """
    ghog.checks.check_data(data)

    rx = data["rx"]
    attrs = dict(data["attrs"])

    ## Taper
    taper = np.ones_like(rx)
    taper[: ntaper // 2, :] = 0
    taper[-ntaper // 2 :, :] = 0
    taper[:, : ntaper // 2] = 0
    taper[:, -ntaper // 2 :] = 0
    taper = scipy.signal.convolve2d(
        taper, np.ones((ntaper, ntaper)) / (ntaper**2), mode="same"
    )
    rx *= taper

    ## Pad
    nt = rx.shape[0]
    nx = rx.shape[1]
    if pt is None:
        pt = 10 * nt

    if px is None:
        px = 1 * nx

    rx = np.pad(rx, ((0, pt), (0, px)), mode="constant", constant_values=0)

    ## Migrate
    cmig = ghog.constants.c / np.sqrt(pmig)
    dt = 1.0 / attrs["fs"]
    dx = attrs["stack_interval"]

    # 2D fft
    RX = np.fft.fftshift(np.fft.fft2(rx))
    w = np.fft.fftshift(np.fft.fftfreq(rx.shape[0], d=dt))
    kx = np.fft.fftshift(np.fft.fftfreq(rx.shape[1], d=dx))

    # Calculate dz and kz values
    dz = dt * cmig / 2
    kz = np.fft.fftshift(np.fft.fftfreq(rx.shape[0], d=dz))

    # Interpolate each column to new w corresponding to kz
    RXmig = np.zeros_like(RX)
    for i in range(RX.shape[1]):
        wkz = np.sign(kz) * (cmig / 2) * np.sqrt(kx[i] ** 2 + kz**2)
        RXmig[:, i] = np.interp(wkz, w, RX[:, i])
        with np.errstate(divide="ignore", invalid="ignore"):
            RXmig[:, i] = RXmig[:, i] * np.abs(
                kz / np.sqrt(kx[i] ** 2 + kz**2)
            )  # obliquity

    RXmig[np.isnan(RXmig)] = 0  # for (kx=0, kz=0)

    # Inverse 2D fft
    RXmig = np.fft.fftshift(RXmig)
    rxmig = np.real(np.fft.ifft2(RXmig))

    # Trim to original dimension
    rxmig = rxmig[:nt, :nx]

    attrs["vmig"] = cmig

    return {"rx": rxmig, "gps": np.copy(data["gps"]), "attrs": attrs}
