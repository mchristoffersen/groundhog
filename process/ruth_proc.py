import h5py
import sys
import matplotlib.pyplot as plt
import numpy as np
import scipy.signal as signal
import pyproj
import pandas as pd
from datetime import datetime
import argparse


def makedd(df):
    # Make decimal degrees from a NRCAN PPP solution dataframe
    neg = df["latdd"] < 0
    df["lat"] = ((-1)**neg)*(np.abs(df["latdd"]) + df["latmn"]/60 + df["latss"]/3600)

    neg = df["londd"] < 0
    df["lon"] = ((-1)**neg)*(np.abs(df["londd"]) + df["lonmn"]/60 + df["lonss"]/3600)

    return df


def syncNav(gps0, posfile):
    # Read in PPP gps record
    cols = [
        "dir",
        "frame",
        "stn",
        "doy",
        "date",
        "time",
        "nsat",
        "gdop",
        "rmsc",
        "rmsp",
        "dlat",
        "dlon",
        "dhgt",
        "sdlat",
        "sdlon",
        "sdhgt",
        "latdd",
        "latmn",
        "latss",
        "londd",
        "lonmn",
        "lonss",
        "hgt",
        "utm_zone",
        "utm_east",
        "utm_north",
        "utm_sclpnt",
        "utm_sclcbn",
    ]
    df = pd.read_csv(posfile, skiprows=6, names=cols, delim_whitespace=True)
    df = makedd(df)
    # Read in emlid gps record
    #cols = ["date", "time", "latitude", "longitude", "height", "Q", "ns", "sdn", "sde", "sdu", "sdne", "sdeu", "sdun", "age", "ratio"]
    #df = pd.read_csv(posfile, comment="%", names=cols, delim_whitespace=True)

    # Merge the date and time columns (just for convenience in reading with datetime)
    df["datetime"] = df["date"] + "T" + df["time"]

    # Convert to datetime objects
    df["datetime"] = pd.to_datetime(df["datetime"], format="%Y/%m/%dT%H:%M:%S.%f")

    # Start of ref epoch is first Emlid fix time
    epoch = df["datetime"][0]

    # Reference all Emlid fixes to that time
    for i in range(len(df["datetime"])):
        df.loc[i, "datetime"] = (df["datetime"][i] - epoch).total_seconds()

    # Get ettus gps fix times
    gpst = np.array([gpst for (lat, lon, hgt, gpst) in gps0], dtype=np.uint64)

    # Convert to datetime then reference to ref epoch
    for i, t in enumerate(gpst):
        t = datetime.utcfromtimestamp(t)
        gpst[i] = (t - epoch).total_seconds()

    # Make sure both are numpy arrays
    gpst = np.array(gpst, dtype=np.float32)
    fixt = np.array(df["datetime"], dtype=np.float32)

    # Interpolate Emlid GPS fixes with trace times
    lati = np.interp(gpst, fixt, df["lat"].to_numpy().astype(np.float32))
    loni = np.interp(gpst, fixt, df["lon"].to_numpy())
    hgti = np.interp(gpst, fixt, df["hgt"].to_numpy())

    return lati, loni, hgti


def calcSep(rxFix, txFix):
    geo = "+proj=longlat +datum=WGS84 +no_defs"
    xyz = "+proj=geocent +no_defs"

    xform = pyproj.Transformer.from_crs(geo, xyz)

    rxx, rxy, rxz = xform.transform(rxFix["lon"], rxFix["lat"], rxFix["hgt"])
    txx, txy, txz = xform.transform(txFix["lon"], txFix["lat"], txFix["hgt"])

    dx = rxx-txx
    dy = rxy-txy
    dz = rxz-txz

    dist = np.sqrt(dx**2 + dy**2 + dz**2)

    return dist


def restack(rx0, rxFix, txFix, intrvl):
    ## Reproject and restack ##
    geo = "+proj=longlat +datum=WGS84 +no_defs"
    xyz = "+proj=geocent +no_defs"
    utm = "+proj=utm +zone=6 +datum=WGS84 +units=m +no_defs"

    xform = pyproj.Transformer.from_crs(geo, xyz)

    x, y, z = xform.transform(rxFix["lon"], rxFix["lat"], rxFix["hgt"])

    dd = np.sqrt(np.diff(x)**2 + np.diff(y)**2 + np.diff(z)**2)
    cumdd = np.cumsum(dd)

    cumdd = np.append(0, cumdd)

    dist = cumdd[-1]  # Total distance
    ntrace = int(dist//intrvl)

    rxRestack = np.zeros((rx0.shape[0], ntrace))
    rxLat = np.zeros(ntrace)
    rxLon = np.zeros(ntrace)
    rxHgt = np.zeros(ntrace)
    txLat = np.zeros(ntrace)
    txLon = np.zeros(ntrace)
    txHgt = np.zeros(ntrace)

    for i in range(ntrace):
        stack_slice = np.logical_and(cumdd > i*intrvl, cumdd < (i+1)*intrvl)
        nstack = np.sum(stack_slice)
        if(nstack == 0):
            rxRestack[:, i] = rxRestack[:, i-1]
            rxLat[i] = rxLat[i-1]
            rxLon[i] = rxLon[i-1]
            rxHgt[i] = rxHgt[i-1]
            txLat[i] = txLat[i-1]
            txLon[i] = txLon[i-1]
            txHgt[i] = txHgt[i-1]
            continue

        rxRestack[:, i] = np.sum(rx0[:, stack_slice], axis=1)/nstack
        rxLat[i] = np.mean(rxFix["lat"][stack_slice])
        rxLon[i] = np.mean(rxFix["lon"][stack_slice])
        rxHgt[i] = np.mean(rxFix["hgt"][stack_slice])
        txLat[i] = np.mean(txFix["lat"][stack_slice])
        txLon[i] = np.mean(txFix["lon"][stack_slice])
        txHgt[i] = np.mean(txFix["hgt"][stack_slice])


    fix_t = np.dtype(
        [("lat", np.float32), ("lon", np.float32), ("hgt", np.float32)]
    )

    rxFixStack = np.empty(len(rxLat), dtype=fix_t)
    txFixStack = np.empty(len(txLat), dtype=fix_t)
    for i in range(len(rxLat)):
        rxFixStack[i] = (rxLat[i], rxLon[i], rxHgt[i])
        txFixStack[i] = (txLat[i], txLon[i], txHgt[i])

    return rxRestack, rxFixStack, txFixStack


def proc(file):
    try:
        fd_old = h5py.File(file, "r")
    except OSError:
        print("Failed to open %s" % file)
        return 1

    i = 0
    t = datetime.utcfromtimestamp(fd_old["gps0"][i][3])
    ref = datetime.strptime("2022", "%Y")
    while t < ref:
        i += 1
        t = datetime.utcfromtimestamp(fd_old["gps0"][i][3])

    name = "./proc/" + datetime.strftime(t, "%Y%m%d_%H%M%S") + ".h5"

    rx0 = fd_old["rx0"][:]
    gps0 = fd_old["gps0"][:]
    fd_old.close()

    # Crop off spare traces if they occur
    if(rx0.shape[1] == 10000):
        sumcol = np.sum(rx0, axis=0)
        rx0 = rx0[:, sumcol != 0]
        gps0 = gps0[sumcol != 0]

    if(len(gps0) <= 10):
        print("Skipping short file %s" % file)
        return 1

    fix_t = np.dtype(
        [("lat", np.float32), ("lon", np.float32), ("hgt", np.float32)]
    )

    # Search index for tx and rx fix files
    ft0 = t #datetime.utcfromtimestamp(gps0[0][3])
    ft1 = datetime.utcfromtimestamp(gps0[-1][3])

    # Pick out and sync rx times
    indx = pd.read_csv("./gps/ppp/rx_indx.txt", names=["file", "start", "stop"])

    rxposfile = ""
    for i, row in indx.iterrows():
        it0 = datetime.strptime(row["start"], "%Y-%m-%dT%H:%M:%S.%f")
        it1 = datetime.strptime(row["stop"], "%Y-%m-%dT%H:%M:%S.%f")
        if(ft0 > it0 and ft1 < it1):
            rxposfile = row["file"]
            break

    if(rxposfile == ""):
        print("No RX GPS found % s" % name)
        return 1

    rxlati, rxloni, rxhgti = syncNav(gps0, rxposfile)

    rxFix0 = np.empty(len(rxlati), dtype=fix_t)
    for i in range(len(rxlati)):
        rxFix0[i] = (rxlati[i], rxloni[i], rxhgti[i])

    # Pick out and sync tx times
    indx = pd.read_csv("./gps/ppp/tx_indx.txt", names=["file", "start", "stop"])

    txposfile = ""
    for i, row in indx.iterrows():
        it0 = datetime.strptime(row["start"], "%Y-%m-%dT%H:%M:%S.%f")
        it1 = datetime.strptime(row["stop"], "%Y-%m-%dT%H:%M:%S.%f")
        if(ft0 > it0 and ft1 < it1):
            txposfile = row["file"]
            break

    if(txposfile == ""):
        print("No TX GPS found % s " % name)
        return 1

    txlati, txloni, txhgti = syncNav(gps0, txposfile)

    txFix0 = np.empty(len(txlati), dtype=fix_t)
    for i in range(len(txlati)):
        txFix0[i] = (txlati[i], txloni[i], txhgti[i])

    raw_sep = calcSep(rxFix0, txFix0)

    # Restack with rx positions
    intrvl = 5
    rx0stack, rxFix0stack, txFix0stack = restack(rx0, rxFix0, txFix0, intrvl)

    # Filter
    fs = 20e6
    sos = signal.butter(4, [0.5e6, 9e6], btype="band", fs=fs, output="sos")
    rx0stack = signal.sosfiltfilt(sos, rx0stack, axis=0)

    # Remove mean trace
    mt = np.mean(rx0stack, axis=1)
    rx0stack = rx0stack - mt[:, np.newaxis]

    # Fix trigger delay
    stack_sep = calcSep(rxFix0stack, txFix0stack)

    fd = h5py.File(name, "x")
    fd_old = h5py.File(file, "r")

    raw = fd.require_group("/raw")

    string_t = h5py.string_dtype(encoding='ascii')

    rx0 = raw.require_dataset("rx0", data=rx0, shape=rx0.shape, dtype=rx0.dtype)
    rx0.attrs.create("fs", fd_old["rx0"].attrs["fs"], dtype=np.uint32)
    rx0.attrs.create("stack", fd_old["rx0"].attrs["stack"], dtype=np.uint32)
    rx0.attrs.create("pre_trigger", fd_old["rx0"].attrs["pre_trigger"], dtype=np.uint32)
    rx0.attrs.create("trigger_threshold", fd_old["rx0"].attrs["trigger_threshold"], dtype=np.float32)
    rx0.attrs.create("desc", "Data digitized and initially stacked by X310", dtype=string_t)

    gps0 = raw.require_dataset("gps0", data=gps0, shape=gps0.shape, dtype=gps0.dtype)
    gps0.attrs.create("desc", "GPS locations and time recorded by X310", dtype=string_t)

    raw.require_dataset("rxFix0", data=rxFix0, shape=rxFix0.shape, dtype=fix_t)
    raw.require_dataset("txFix0", data=txFix0, shape=txFix0.shape, dtype=fix_t)

    raw_sep_ds = raw.require_dataset("sep", data=raw_sep, shape=raw_sep.shape, dtype=np.float32)
    raw_sep_ds.attrs.create("desc", "Separation in meters between RX and TX sled", dtype=string_t)
    
    raw.require_dataset("rxFix0", data=rxFix0, shape=rxFix0.shape, dtype=fix_t)
    raw.require_dataset("txFix0", data=txFix0, shape=txFix0.shape, dtype=fix_t)

    raw_sep_ds = raw.require_dataset("sep", data=raw_sep, shape=raw_sep.shape, dtype=np.float32)
    raw_sep_ds.attrs.create("desc", "Separation in meters between RX and TX sled", dtype=string_t)

    rstk = fd.require_group("restack")
    rx0stack_ds = rstk.require_dataset("rx0", data=rx0stack, shape=rx0stack.shape, dtype=np.float32)
    rx0stack_ds.attrs.create("stack_interval", "%d meters" % intrvl, dtype=string_t)

    rstk.require_dataset("rxFix0", data=rxFix0stack, shape=rxFix0stack.shape, dtype=fix_t)
    rstk.require_dataset("txFix0", data=txFix0stack, shape=txFix0stack.shape, dtype=fix_t)

    stack_sep_ds = rstk.require_dataset("sep", data=stack_sep, shape=stack_sep.shape, dtype=np.float32)
    stack_sep_ds.attrs.create("desc", "Separation in meters between RX and TX sled", dtype=string_t)

    fd.close()
    fd_old.close()

    return 0


def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('files', nargs='+',
                        help='files to process')

    args = parser.parse_args()

    for file in args.files:
        fail = False
        if(proc(file)):
            fail = True
        orig_name


main()
