# Groundhog HDF5 I/O operations
import h5py
import os
import numpy as np

import ghog.checks


def load(file, group="raw"):
    """Load a group from a Groundhog HDF5 file into memory.

    Args:
        file: Groundhog HDF5 data file.
        group: Group in the HDF5 file to load (default = "raw").

    Returns:
        Dictionary containing the 2D data array (rx), numpy structured array with per-column
        positions and times (gps), and data attributes (attrs).
    """
    if type(file) != str:
        raise TypeError("file is not a string.")

    if type(group) != str:
        raise TypeError("group is not a string.")

    if not os.path.isfile(file):
        raise ValueError("%s is not a file." % file)

    with h5py.File(file, mode="r") as fd:
        rx = fd[group]["rx0"][:]
        gps = fd[group]["gps0"][:]
        attrs = dict(fd[group]["rx0"].attrs.items())

    return {"rx": rx, "gps": gps, "attrs": attrs}


def save(file, data, group="proc", overwrite=False):
    """Save a group to a Groundhog HDF5 file.

    Args:
      file: Groundhog HDF5 data file.
      data: Groundhog data dictionary (rx, gps, attrs).
      group: Group to save to in the HDF5 file (default = "proc").
      overwrite: Overwrite a group if it already exists in an HDF5 file (default = False).
    """
    ghog.checks.check_data(data)

    if type(file) != str:
        raise TypeError("file is not a string.")

    if type(group) != str:
        raise TypeError("group is not a string.")

    if type(overwrite) != bool:
        raise TypeError("overwrite is not a boolean.")

    with h5py.File(file, mode="a") as fd:
        if group in fd:
            if not overwrite:
                raise ValueError(
                    "The group %s already exists in %s. Use overwrite=True to overwrite it."
                    % (group, file)
                )
            else:
                del fd[group]

        # Build group/datasets
        fd.create_group(group)
        fd[group].create_dataset("rx0", data=data["rx"])
        fd[group].create_dataset("gps0", data=data["gps"])
        for k, v in data["attrs"].items():
            fd[group]["rx0"].attrs[k] = v
