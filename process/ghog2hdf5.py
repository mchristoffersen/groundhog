#!/usr/bin/python3

import struct
import argparse
import os
import time
import calendar
import traceback

import numpy as np
import h5py
import glob


def cli():
    # Command line interface
    parser = argparse.ArgumentParser(
        description="Convert Groundhog digitizer files to HDF5"
    )
    parser.add_argument(
        "files",
        type=str,
        help="Digitizer file(s) to convert to HDF5",
        nargs="+"
    )
    args = parser.parse_args()
    return args


def parseHeader(data, file):
    if data[0:4] != b"\xef\xbe\xd0\xd0":
        print(
            file,
            "is improperly formed Groundhog digitizer file, missing header segment magic bytes.",
        )
        return -1

    header = {}

    header["spt"] = struct.unpack("q", data[4:12])[0]
    header["pre_trig"] = struct.unpack("q", data[12:20])[0]
    header["prf"] = struct.unpack("q", data[20:28])[0]
    header["stack"] = struct.unpack("q", data[28:36])[0]
    header["trig"] = struct.unpack("h", data[36:38])[0]
    header["fs"] = struct.unpack("d", data[38:46])[0]

    return header


def parseTraces(data, spt, file):
    partial = False
    bpt = 8 * spt + 26  # bytes per trace

    if data[0:4] != b"\xce\xfa\xed\xfe":
        print(
            file,
            "is improperly formed Groundhog digitizer file, missing data segment magic bytes.",
        )
        return -1, -1

    if data[-4:] != b"\xad\xde\xad\xde":
        print(
            file,
            "is improperly formed Groundhog digitizer file, missing file end magic bytes.",
        )
        print("Will continue attempt to convert")
        partial = True

    ntrace = (len(data) - 8) / bpt

    if ntrace != int(ntrace):
        if partial:
            nkeep = int(ntrace) * bpt + 4
            data = data[:nkeep]
        else:
            print("File appears corrupted (some partial traces missing)")
            print("Need to implement reader for this")
            return -1, -1

    ntrace = int(ntrace)
    rx = np.zeros((spt, ntrace), dtype=np.int64)
    times = []

    data = data[4:]
    for i in range(ntrace):
        times.append(data[i * bpt : i * bpt + 26].decode("utf-8"))
        rx[:, i] = struct.unpack("q" * spt, data[i * bpt + 26 : (i + 1) * bpt])

    return rx, times


def buildH5(header, rx, gps, file):
    try:
        fname = os.path.basename(file).replace(".ghog", "")
        if(gps is not None):
            time0 = time.gmtime(gps["utc"][0])
            time0 = time.strftime("%Y-%m-%dT%H-%M-%S", time0)
        else:
            time0 = "unk"
        outfile = (
            os.path.dirname(file)
            + "/"
            + time0
            + "_"
            + fname
            + ".h5"
        )
        print("Saving ", outfile)

        fd = h5py.File(outfile, "w")

        raw = fd.create_group("raw")
        raw.create_dataset("rx0", data=rx)

        if(gps is not None):
            raw.create_dataset("gps0", data=gps)

        for k, v in header.items():
            raw.attrs[k] = v

        fd.close()
    except Exception as e:
        print(e)
        return -1

    return 0


def DDMtoDD(ddm):
    d = np.float64(ddm[:-7])
    m = np.float64(ddm[-7:]) / 60.0
    return d + m


def parseGPS(file):
    try:
        nmeas = open(file, mode="r").read().splitlines()
    except Exception as e:
        print(e)
        return -1, -1

    gpgga = []
    gpzda = []
    tgpgga = []
    tgpgza = []
    for i, nmea in enumerate(nmeas):
        if "class" in nmea:
            # skip json info strings
            continue

        syst, fix = nmea.split("$", maxsplit=1)

        if "GPGGA" in fix:
            gpgga.append(fix)
            tgpgga.append(syst)

        if "GPZDA" in fix:
            gpzda.append(fix)
            tgpgza.append(syst)

    if(len(gpgga) != len(gpzda)):
        print("Number of GPGGA strings != number of GPZDA string, need to handle this")
        return -1, -1

    fix = np.zeros((len(gpgga), 4))  # lon, lat, hgt, utc
    for i in range(len(gpgga)):
        gga = gpgga[i].split(",")
        zda = gpzda[i].split(",")
        if(gga[1] != zda[1]):
            print("GPGGA and GPZDA misalignment, need to handle this")
            return -1, -1

        fix[i, 1] = DDMtoDD(gga[2])
        fix[i, 0] = DDMtoDD(gga[4])
        fix[i, 2] = gga[9]

        if gga[3] == "S":
            fix[i, 1] *= -1

        if gga[5] == "W":
            fix[i, 0] *= -1

        # Convert UTC time to seconds since epoch
        fix[i, 3] = calendar.timegm(time.strptime(zda[4] + zda[3] + zda[2] + zda[1], "%Y%m%d%H%M%S.%f"))

    return tgpgga, fix


def interpFix(timesGps, timesFile, fix):
    # Reference everyting to first GPS time
    timesGps = np.array([calendar.timegm(time.strptime(t.strip(), "%Y-%m-%d %H:%M:%S.%f:")) for t in timesGps])
    timesFile = np.array([calendar.timegm(time.strptime(t.strip(), "%Y-%m-%dT%H:%M:%S.%f")) for t in timesFile])

    # Check for suspicious things
    if(timesGps[0] > timesFile[0] or timesGps[-1] < timesFile[-1]):
        print("GPS times do not entirely contain data file times, proceed with caution")

    loni = np.interp(timesFile, timesGps, fix[:,0])
    lati = np.interp(timesFile, timesGps, fix[:,1])
    hgti = np.interp(timesFile, timesGps, fix[:,2])
    timei = np.interp(timesFile, timesGps, fix[:,3])

    return np.stack((loni, lati, hgti, timei)).T

def restack(rx0, rxFix, txFix, intrvl, skip=False):
    ## Reproject and restack ##
    # This will need to be modified to work with single gps data

    if(skip):
        return rx0, rxFix, txFix

    geo = "+proj=longlat +datum=WGS84 +no_defs"
    xyz = "+proj=geocent +no_defs"
    utm = "+proj=utm +zone=6 +datum=WGS84 +units=m +no_defs"

    xform = pyproj.Transformer.from_crs(geo, xyz)

    x, y, z = xform.transform(rxFix["lon"], rxFix["lat"], rxFix["hgt"])

    dd = np.sqrt(np.diff(x)**2 + np.diff(y)**2 + np.diff(z)**2)
    plt.plot(dd)

    dd[dd <= .5] = 0

    cumdd = np.cumsum(dd)
    cumdd = np.append(0, cumdd)
    
    #plt.figure()
    #plt.plot(cumdd)
    #plt.figure()
    #plt.plot(dd)
    #plt.show()
    # Use np.interp
    #ddint = np.array(range(0, int(cumdd[-1]), intrvl))
    #rxInt = np.zeros((rx0.shape[0], len(ddint)), dtype=np.float32)
    #for i in range(rx0.shape[0]):
    #    rxInt[i, :] = np.interp(ddint, cumdd, rx0[i, :])

    #plt.imshow(rxInt, cmap="Greys", vmin=np.percentile(rxInt, 5), vmax=np.percentile(rxInt, 95), aspect="auto")
    #plt.show()

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

# lon, lat, hgt, utc
    fix_t = np.dtype(
        [("lat", np.float32), ("lon", np.float32), ("hgt", np.float32)]
    )

    #plt.imshow(rxRestack, cmap="Greys", vmin=np.percentile(rxRestack, 5), vmax=np.percentile(rxRestack, 95), aspect="auto")
    #plt.show()

    rxFixStack = np.empty(len(rxLat), dtype=fix_t)
    txFixStack = np.empty(len(txLat), dtype=fix_t)
    for i in range(len(rxLat)):
        rxFixStack[i] = (rxLat[i], rxLon[i], rxHgt[i])
        txFixStack[i] = (txLat[i], txLon[i], txHgt[i])

    return rxRestack, rxFixStack, txFixStack

def main():
    args = cli()

    for file in args.files:
        try:
            print("Converting " + file)
            try:
                fd = open(file, "rb")
            except Exception as e:
                print(e)
                continue

            data = fd.read()
            fd.close()

            if len(data) < 46:
                print(
                    "%s - Incomplete file, only partial header present. Skipping conversion" % file
                )
                continue

            header = parseHeader(data, file)

            if header == -1:
                print("%s - Failed to parse file header" % file)
                continue

            rx, timesFile = parseTraces(data[46:], header["spt"], file)

            if timesFile == -1:
                print("%s - Failed to parse file data segment" % file)
                continue

            gpsFile = file.replace(".ghog", ".txt")
            if(not os.path.isfile(gpsFile)):
                print("%s - No GPS file found. No GPS information will be included in HDF5." % file)
                fix = None
                gps = None
            else:
                timesGps, fix = parseGPS(gpsFile)

                if timesGps == -1:
                    print(
                        "%s - Failed to parse GPS file. No GPS information will be included in HDF5." % file
                    )
                    fix = None
                    gps = None
                else:
                    fix = interpFix(timesGps, timesFile, fix)

            # get fix to right datattype for hdf5
            if(fix is not None):
                gps_t = np.dtype([("lon", "f8"), ("lat", "f8"), ("hgt", "f8"), ("utc", "f8")])
                gps = [None]*fix.shape[0]
                for i in range(fix.shape[0]):
                    gps[i] = tuple(fix[i,:])
                gps = np.array(gps, dtype=gps_t)


            if buildH5(header, rx, gps, file) == -1:
                print("%s - Failed to build HDF5." % file)
                continue

            print()

        except Exception as e:
            print(e)
            print(traceback.format_exc())
            print("%s - Unanticipated failure. Skipping conversion." % file)

    return 0


main()
