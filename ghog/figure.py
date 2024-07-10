# Generate radargram figure
import numpy as np
import matplotlib.pyplot as plt
import pyproj

import ghog.checks
import ghog.constants


def figure(
    data,
    file="radargram.png",
    xunit="distance",
    yunit="time",
    pdepth=3.15,
    figsize=(8, 4),
    pclip=1,
    tpow=0,
    cmap="seismic",
    show=False,
):
    """Generate radargram figure.

    Args:
        data: Groundhog data dictionary (rx, gps, attrs).
        file: File name to save figure at. To not save an image
            use filename=None (default = "radargram.png").
        xunit: Unit for x axis, valid options are ["index", "distance"] (default = "distance").
        yunit: Unit for y axis, valid options are ["index", "time", "depth"] if "depth"
            is chosen the pdepth argument is used to convert time to depth (default = "time").
        pdepth: Relative permittivity for y axis depth conversion (default = 3.15).
        figsize: Figure dimension (x, y) in inches (default = (8, 4)).
        pclip: Linear scaling clip percent, between 0 and 50 (default = 1).
        tpow: Power of time exponential gain (default = 0 : no gain).
        cmap: Matplotlib colormap to use (default = "seismic").
        show: Show figure in desktop window (default = False).
    """
    ghog.checks.check_data(data)

    if type(file) is not str:
        raise TypeError("file must be a string.")

    legal_xunit = ["index", "distance"]
    if xunit not in legal_xunit:
        raise ValueError(
            "Invalid xunit argument: %s. xunit must be one of: %s"
            % (xunit, legal_xunit)
        )

    legal_yunit = ["index", "time", "depth"]
    if yunit not in legal_yunit:
        raise ValueError(
            "Invalid yunit argument: %s. yunit must be one of: %s"
            % (yunit, legal_yunit)
        )

    if type(figsize) != tuple and type(figsize) != list:
        raise TypeError("figsize must be tuple or list")

    if len(figsize) != 2:
        raise ValueError("Length of figsize must be 2.")

    if pclip < 0 or pclip >= 50:
        raise ValueError("pclup must be greater than or equal to 0 and less than 50")

    if type(show) is not bool:
        raise TypeError("show must be a boolean.")

    if pdepth < 1:
        raise ValueError("pdepth cannot be less than one.")

    rx = np.copy(data["rx"])
    gps = data["gps"]
    attrs = data["attrs"]

    # Set up x extent
    xmin = 0
    if xunit == "index":
        xmax = rx.shape[1]
        xlabel = "Trace index"
    elif xunit == "distance":
        xform = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:4978")
        x, y, z = xform.transform(gps["lat"], gps["lon"], gps["hgt"])
        steps = np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2 + np.diff(z) ** 2)
        xmax = np.sum(steps)
        xlabel = "Distance along profile (m)"

    # Set up y extent
    if yunit == "index":
        ymin = 0
        ymax = rx.shape[0]
        ylabel = "Sample index"
    elif yunit == "time":
        t = (np.arange(rx.shape[0]) - attrs["pre_trig"]) / attrs["fs"]
        ymin = np.min(t) * 1e6
        ymax = np.max(t) * 1e6
        ylabel = "Time ($\\mu$s)"
    elif yunit == "depth":
        t = (np.arange(rx.shape[0]) - attrs["pre_trig"]) / attrs["fs"]
        cdepth = ghog.constants.c / np.sqrt(pdepth)
        ymin = np.min(t) * cdepth / 2
        ymax = np.max(t) * cdepth / 2
        ylabel = "Depth (m)"

    # Apply gain
    gain = np.arange
    t = (np.arange(rx.shape[0]) - attrs["pre_trig"]) / attrs["fs"]
    gain = t**tpow
    gain = gain / np.max(gain)
    rx = rx * gain[:, np.newaxis]

    # Generate figure
    fig, ax = plt.subplots(1, 1, figsize=figsize)
    plt.imshow(
        rx,
        extent=[xmin, xmax, ymax, ymin],
        vmin=np.percentile(rx, pclip),
        vmax=np.percentile(rx, 100 - pclip),
        aspect="auto",
        cmap=cmap,
    )
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    if file is not None:
        fig.savefig(file, bbox_inches="tight", dpi=300)

    if show:
        plt.show()
