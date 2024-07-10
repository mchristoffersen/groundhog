# Filtering wrapper
import numpy as np
import scipy.signal

import ghog.checks


def filt(data, passband, axis=0, order=4):
    """Apply a Butterworth filter along a data axis.

    Forward and backward for zero phase shift.

    Args:
        data: Groundhog data dictionary (rx, gps, attrs).
        passband: (low, high) Tuple giving passband for filter, assumes units of hertz if
            axis=0, assumes wavenumber if axis=1 and stack_interval exists in attrs,
            otherwise assumes fraction of nyquist. Use None to denote no filter edge and
            create a low pass or high pass filter.
        axis: Axis to filter along (default = 0).
        order: Filter order (default = 4).

    Returns:
        Dictionary containing the filtered 2D data array (rx), numpy structured array with per-column
        positions and times (gps), and data attributes (attrs).

    Example:
        Examples can be given using either the ``Example`` or ``Examples``
        sections. Sections support any reStructuredText formatting, including
        literal blocks::

            $ python example_google.py
    """
    ghog.checks.check_data(data)

    if passband == (None, None):
        raise ValueError("Both filter edges cannot be None.")

    if axis not in [0, 1]:
        raise ValueError("Axis must be 0 or 1.")

    if order <= 0:
        raise ValueError("Order cannot be 0 or negative.")

    if passband[0] is None:
        Wn = passband[1]
        btype = "lowpass"
    elif passband[1] is None:
        Wn = passband[0]
        btype = "highpass"
    else:
        Wn = passband
        btype = "bandpass"

    if axis == 0:
        fs = data["attrs"]["fs"]
    elif axis == 1 and "stack_interval" in data["attrs"]:
        fs = 1.0 / data["attrs"]["stack_interval"]
    else:
        fs = None

    sos = scipy.signal.iirfilter(
        order, Wn, btype=btype, analog=False, ftype="butter", output="sos", fs=fs
    )

    rx = scipy.signal.sosfiltfilt(sos, data["rx"], axis=axis, padlen=256)

    return {"rx": rx, "gps": np.copy(data["gps"]), "attrs": dict(data["attrs"])}
