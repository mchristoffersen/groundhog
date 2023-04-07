#!/usr/bin/python3

import struct
import argparse
import os

import numpy as np
import h5py
import matplotlib.pyplot as plt
import glob


def cli():
    # Command line interface
    parser = argparse.ArgumentParser(
        description="Convert Groundhog digitizer files to HDF5"
    )
    parser.add_argument(
        "files",
        type=str,
        nargs="+",
        help="Groundhog digitizer file(s) to convert to HDF5",
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
        outfile = os.path.dirname(file) + "/" + times[0].replace(":", "-") + "_" + fname + ".h5"
        print("Saving ", outfile)

        fd = h5py.File(outfile, "w")

        raw = fd.create_group("raw")
        raw.create_dataset("rx", data=rx)
        raw.create_dataset("time", data=times)

        for k, v in header.items():
            raw.attrs[k] = v

        fd.close()
    except Exception as e:
        print(e)
        return -1

    return 0


def main():
    #args = cli()
    #for file in args.files:
    
    # Hardcoding data location 
    data_dir = "/home/radar/groundhog/data/*.dat"

    for file in glob.glob(data_dir):
        print("Converting " + file)
        try:
            fd = open(file, "rb")
        except Exception as e:
            print(e)
            continue

        data = fd.read()
        fd.close()

        if len(data) < 46:
            print("Incomplete file, only partial header present\n")
            continue

        header = parseHeader(data, file)

        if header == -1:
            print("Failed to parse file header\n")
            continue

        rx, times = parseTraces(data[46:], header["spt"], file)

        if times == -1:
            print("Failed to parse file data segment\n")
            continue

        if (buildH5(header, rx, times, file) == -1):
            print("Faild to build HDF5\n")
            continue

        print()

    return 0


main()
