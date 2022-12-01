import matplotlib.pyplot as plt
import pandas as pd
import rasterio as rio
import pyproj
from datetime import datetime
import numpy as np

# Load pos files for tx and rx
# May 7
tx_file = "/home/mchristo/proj/field/Ruth2022/ruth_data_processor/gps/single/DOOOO_raw_202205071853.pos"
rx_file = "/home/mchristo/proj/field/Ruth2022/ruth_data_processor/gps/single/SCOOBY_raw_202205071847.pos"

cols = ["date", "time", "latitude", "longitude", "height", "Q", "ns", "sdn", "sde", "sdu", "sdne", "sdeu", "sdun", "age", "ratio"]
tx = pd.read_csv(tx_file, comment="%", names=cols, delim_whitespace=True)
rx = pd.read_csv(rx_file, comment="%", names=cols, delim_whitespace=True)


# Load basemap (Ruth area hillshade)
base = "/home/mchristo/proj/field/Ruth2022/ifsar/USGS_AK5M_RUTH_HS.tif"
bm = rio.open(base, "r")


# Convert tx and rx coordinates to basemap coordinates and basemap pixel indices
navcrs = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
transformer = pyproj.Transformer.from_crs(navcrs, bm.crs)

# Basemap crs
tx["x"], tx["y"] = transformer.transform(tx["longitude"].to_numpy(), tx["latitude"].to_numpy())
rx["x"], rx["y"] = transformer.transform(rx["longitude"].to_numpy(), rx["latitude"].to_numpy())

# Basemap row/column
gt = ~bm.transform
tx["ix"], tx["iy"] = gt * (tx["x"], tx["y"])
rx["ix"], rx["iy"] = gt * (rx["x"], rx["y"])


# Make a datatime field to match the two location records
tx["datetime"] = tx["date"] + "T" + tx["time"]
rx["datetime"] = rx["date"] + "T" + rx["time"]

tx["datetime"] = pd.to_datetime(tx["datetime"], format="%Y/%m/%dT%H:%M:%S.%f")
rx["datetime"] = pd.to_datetime(rx["datetime"], format="%Y/%m/%dT%H:%M:%S.%f")


# Find overlap of two files
if(len(rx[rx["datetime"] == tx["datetime"][0]]) > 0):
    startt = tx["datetime"][0]
else:
    startt = rx["datetime"][0]

if(len(rx[rx["datetime"] == tx["datetime"][len(tx)-1]]) > 0):
    stopt = tx["datetime"][len(tx)-1]
else:
    stopt = rx["datetime"][len(rx)-1]

t = startt

# Set step, this works since all rx positions are 1Hz
step = 10 # seconds
step = rx["datetime"][step] - rx["datetime"][0]  # 10 seconds 


# Initialize variables for plotting
txx = tx[tx["datetime"] == t]["x"].to_numpy()[0]
txy = tx[tx["datetime"] == t]["y"].to_numpy()[0]
rxx = rx[rx["datetime"] == t]["x"].to_numpy()[0]
rxy = rx[rx["datetime"] == t]["y"].to_numpy()[0]

cx = (txx+rxx)/2
cy = (txy+rxy)/2

icx, icy = (~bm.transform) * (cx, cy)


# Number of DEM pixels to add around GPS position
pad = 1050
bounds = [icx-pad, icx+pad, icy-pad, icy+pad]
lx, ly = bm.transform * (np.array(bounds[:2]), np.array(bounds[2:]))


# When to switch over to the next DEM frame
xpad = 25
xbounds = [bounds[0]-xpad, bounds[1]+xpad, bounds[2]-xpad, bounds[3]+xpad]
vlx, vly = bm.transform * (np.array(xbounds[:2]), np.array(xbounds[2:]))

rowSub = (xbounds[2], xbounds[3])
colSub = (xbounds[0], xbounds[1])

win = rio.windows.Window.from_slices(rowSub, colSub)

data = bm.read(1, window=win)

rectxx = np.array([])
rectxy = np.array([])
recrxx = np.array([])
recrxy = np.array([])


# Function to check if you have left the DEM window
def badBox(txx, txy, rxx, rxy, lx, ly):
    for c in [txx, rxx]:
        if(c < lx[0]):
            return 1
        if(c > lx[1]):
            return 2

    for c in [txy, rxy]:
        if(c > ly[0]):
            return 3
        if(c < ly[1]):
            return 4

    return 0


# Make frames for video
while t < stopt-step:
    # Update frame
    t = t + step

    try:
        txx = tx[tx["datetime"] == t]["x"].to_numpy()[0]
        txy = tx[tx["datetime"] == t]["y"].to_numpy()[0]
        rxx = rx[rx["datetime"] == t]["x"].to_numpy()[0]
        rxy = rx[rx["datetime"] == t]["y"].to_numpy()[0]
    except IndexError:
        # Skip if there is no matching solution, this happens sometimes
        print("SKIPPED FRAME T=", t)
        continue

    # Maintain record of last 2 positions
    rectxx = np.append(txx, rectxx)
    rectxy = np.append(txy, rectxy)
    recrxx = np.append(rxx, recrxx)
    recrxy = np.append(rxy, recrxy)

    reclen = 2
    rectxx = rectxx[:reclen]
    rectxy = rectxy[:reclen]
    recrxx = recrxx[:reclen]
    recrxy = recrxy[:reclen]

    if(badBox(txx, txy, rxx, rxy, lx, ly)):
        side = badBox(txx, txy, rxx, rxy, lx, ly)
        # Decide which way to move the DEM window
        if(side == 1):
            bounds[1], y = (~bm.transform) * (max(np.append(rectxx, recrxx)), 0)
            bounds[0] = bounds[1] - 2*pad
        elif(side == 2):
            bounds[0], y = (~bm.transform) * (min(np.append(rectxx, recrxx)), 0)
            bounds[1] = bounds[0] + 2*pad
        elif(side == 3):
            x, bounds[3] = (~bm.transform) * (0, min(np.append(rectxy, recrxy)))
            bounds[2] = bounds[3] - 2*pad
        elif(side == 4):
            x, bounds[2] = (~bm.transform) * (0, max(np.append(rectxy, recrxy)))
            bounds[3] = bounds[2] + 2*pad

        # Load in a subset of the Ruth hillshade
        lx, ly = bm.transform * (np.array(bounds[:2]), np.array(bounds[2:]))

        # Add extra padding to frame
        xpad = 25
        xbounds = [bounds[0]-xpad, bounds[1]+xpad, bounds[2]-xpad, bounds[3]+xpad]
        vlx, vly = bm.transform * (np.array(xbounds[:2]), np.array(xbounds[2:]))

        rowSub = (xbounds[2], xbounds[3])
        colSub = (xbounds[0], xbounds[1])

        win = rio.windows.Window.from_slices(rowSub, colSub)

        data = bm.read(1, window=win)

    plt.imshow(data, extent=[vlx[0], vlx[1], vly[1], vly[0]], cmap="Greys_r")
    plt.gca().get_xaxis().set_visible(False)
    plt.gca().get_yaxis().set_visible(False)

    for i in range(len(rectxx)):
        plt.plot(rectxx[i], rectxy[i], "r.", alpha=1-((1/reclen)*i))

    for i in range(len(recrxx)):
        plt.plot(recrxx[i], recrxy[i], "b.", alpha=1-((1/reclen)*i))

    label = datetime.strftime(t, "%Y%m%dT%H%M%S")
    plt.title(label)
    plt.savefig("./animate/%s.png" % label, dpi=200, bbox_inches="tight")
    plt.cla()