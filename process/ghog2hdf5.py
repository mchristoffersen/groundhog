#!/usr/bin/python3

import struct
import argparse
import os
import time

import numpy as np
import h5py
import glob


def cli():
    # Command line interface
    parser = argparse.ArgumentParser(
        description="Convert Groundhog digitizer files to HDF5"
    )
    parser.add_argument(
        "--dir",
        type=str,
        help="Directory of digitizer file(s) to convert to HDF5",
        default="/home/radar/groundhog/data",
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
    bpt = 8 * spt + 19  # bytes per trace

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
        times.append(data[i * bpt : i * bpt + 19].decode("utf-8"))
        rx[:, i] = struct.unpack("q" * spt, data[i * bpt + 19 : (i + 1) * bpt])

    return rx, times


def buildH5(header, rx, times, file):
    try:
        fname = os.path.basename(file).replace(".dat", "")
        outfile = (
            os.path.dirname(file)
            + "/"
            + times[0].replace(":", "-")
            + "_"
            + fname
            + ".h5"
        )
        print("Saving ", outfile)

        fd = h5py.File(outfile, "w")

        raw = fd.create_group("raw")
        raw.create_dataset("rx0", data=rx)
        raw.create_dataset("time", data=times)

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

    fixs = []
    systs = []
    for i, nmea in enumerate(nmeas):
        if "class" in nmea:
            # skip json info strings
            continue

        syst, fix = nmea.split("$", maxsplit=1)

        if "GPGGA" in fix:
            fixs.append(fix)
            systs.append(syst)

    gps = np.zeros((len(fixs), 4))  # lon, lat, hgt, time
    for i, fix in enumerate(fixs):
        fix = fix.split(",")
        gps[i, 3] = np.float64(fix[1])
        gps[i, 1] = DDMtoDD(fix[2])
        gps[i, 0] = DDMtoDD(fix[4])
        gps[i, 2] = fix[9]

        if fix[3] == "S":
            gps[i, 1] *= -1

        if fix[5] == "W":
            gps[i, 0] *= -1

    return systs, gps


def interpFix(timesGps, timesFile, fix):
    timesGps = np.array([time.mktime(time.strptime(t.strip(), "%Y-%m-%d %H:%M:%S:")) for t in timesGps])
    timesFile = np.array([time.mktime(time.strptime(t.strip(), "%Y-%m-%dT%H:%M:%S")) for t in timesFile])
    # Interpolate repeated file times
    _, uidx = np.unique(timesFile, return_index=True)
    idx = np.arange(len(timesFile))
    timesFile = np.interp(idx, uidx, timesFile[uidx])
    print(np.diff(timesFile))


def main():
    args = cli()
    files = glob.glob(args.dir + "/*.dat")

    if len(files) == 0:
        print("No data files found, exiting")

    for file in files:
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
                    "Incomplete file, only partial header present -- skipping conversion\n"
                )
                continue

            header = parseHeader(data, file)

            if header == -1:
                print("Failed to parse file header\n")
                continue

            rx, timesFile = parseTraces(data[46:], header["spt"], file)

            if timesFile == -1:
                print("Failed to parse file data segment\n")
                continue

            gpsFile = file.replace(".dat", ".txt")
            timesGps, fix = parseGPS(gpsFile)

            if timesGps == -1:
                print(
                    "No GPS file found or failed to parse GPS file -- skipping conversion\n"
                )
                continue

            gps = interpFix(timesGps, timesFile, fix)

            if buildH5(header, rx, times, file) == -1:
                print("Faild to build HDF5\n")
                continue

            print()

        except Exception as e:
            print(e)
            print("Unanticipated failure -- skipping conversion\n")

    return 0


main()
