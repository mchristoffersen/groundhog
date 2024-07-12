import numpy as np

import ghog.checks


def mute(data, indices, axis=0):
    """Apply a mute to rows or columns of the data.

    Args:
        data: Groundhog data dictionary (rx, gps, attrs).
        indices: Indices of the rows or columns to mute.
        axis: Axis on which to apply the mute (default = 0 : mute columns).

    Returns:
        Dictionary containing the muted 2D data array (rx), numpy structured array with
        per-column positions and times (gps), and data attributes (attrs).
    """
    if type(indices) != list and type(indices) != tuple and type(indices) != np.ndarray:
        raise TypeError("indices must be a list, tuple, or numpy ndarray")
    
    # TODO: add tapering here
    rxmute = np.copy(data["rx"])

    for i in indices:
        if(axis == 0):
            rxmute[:,i] = 0
        elif(axis == 1):
            rxmute[i, :] = 0

    return {"rx": rxmute, "gps": np.copy(data["gps"]), "attrs": dict(data["attrs"])}
