import matplotlib.pyplot as plt
import pandas as pd
import rasterio as rio
import pyproj
from datetime import datetime
import numpy as np
import sys
import h5py
import scipy.signal as signal

# Load data file
radar_file = "./proc/20220505_202734.h5"
fd = h5py.File(radar_file, "r")
fs = 20e6

# Load basemap (Ruth area hillshade)
base = "/home/mchristo/proj/field/Ruth2022/ifsar/USGS_AK5M_RUTH_HS.tif"
bm = rio.open(base, "r")

# Get out lat lon
txLat = np.array([lat for (lat, lon, hgt) in fd["/raw/txFix0"]])
txLon = np.array([lon for (lat, lon, hgt) in fd["/raw/txFix0"]])

rxLat = np.array([lat for (lat, lon, hgt) in fd["/raw/rxFix0"]])
rxLon = np.array([lon for (lat, lon, hgt) in fd["/raw/rxFix0"]])

# Convert tx and rx coordinates to basemap coordinates and basemap pixel indices
# Then calculate basemap bounds
navcrs = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"
transformer = pyproj.Transformer.from_crs(navcrs, bm.crs)

txx, txy = transformer.transform(txLon, txLat)
rxx, rxy = transformer.transform(rxLon, rxLat)

gt = ~bm.transform
txix, txiy = gt * (txx, txy)
rxix, rxiy = gt * (rxx, rxy)

pad = 250
minx = float(min(np.append(txix, rxix)))
maxx = float(max(np.append(txix, rxix)))
miny = float(min(np.append(txiy, rxiy)))
maxy = float(max(np.append(txiy, rxiy)))

bounds = [minx-pad, maxx+pad, miny-pad, maxy+pad]
lx, ly = bm.transform * (np.array(bounds[:2]), np.array(bounds[2:]))

rowSub = (bounds[2], bounds[3])
colSub = (bounds[0], bounds[1])

print(bounds)
win = rio.windows.Window.from_slices(rowSub, colSub)

bmap = bm.read(1, window=win)

rx0 = fd["/raw/rx0"]
sos = signal.butter(4, [0.5e6, 8.5e6], btype="band", fs=fs, output="sos")
rx0 = signal.sosfiltfilt(sos, rx0, axis=0)
img = np.log(np.abs(rx0))
vmin = np.percentile(img, 20)
vmax = np.percentile(img, 99)

#fig, ax = plt.subplots(2, figsize=(20,10), gridspec_kw={"width_ratios": [1,4]})
for i in range(0, len(txx), 10):
    plt.subplot(1,2,1)
    plt.imshow(bmap, extent=[lx[0], lx[1], ly[1], ly[0]], cmap="Greys_r")
    plt.plot(txx[i], txy[i], 'ro')

    img = np.log(np.abs(rx0))
    img[:, i+1:] = np.nan
    plt.subplot(1, 2, 2)
    plt.imshow(img, aspect="auto", cmap="Greys_r", vmin=vmin, vmax=vmax)
    
    plt.savefig("./track_dat/%d.png" % i)
    plt.cla()

fd.close()
plt.set_y