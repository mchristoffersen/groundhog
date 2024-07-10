# Merge CSRS PPP solutions into HDF5 files
import argparse
import numpy as np
import h5py
import pandas as pd
import matplotlib.pyplot as plt


def cli():
    # Command line interface
    parser = argparse.ArgumentParser(
        description="Merge CSRS PPP solutions into Groundhog HDF5 files"
    )
    parser.add_argument("hdf5", type=str, help="HDF5 Files", nargs="+")
    parser.add_argument("pos", type=str, help="CSRS .pos Files", nargs="+")
    args = parser.parse_args()
    return args


def main():
    args = cli()

    # Sort hdf5 from pos files
    files = args.hdf5 + args.pos

    hdf5 = []
    position = {}
    for file in files:
        if file.lower()[-3:] == ".h5":
            hdf5.append(file)
        elif file.lower()[-4:] == ".pos":
            position[file] = None
        else:
            print("Unrecognized file " + file)

    # Get time bounds of each pos file
    posBounds = {}
    for file in position.keys():
        df = pd.read_csv(file, skiprows=3, delimiter="\\s+")

        # Make datetime64
        df["datetime"] = df["YEAR-MM-DD"] + "T" + df["HR:MN:SS.SS"]
        df["datetime"] = df["datetime"].apply(np.datetime64)

        # Convert lon and lat to decimal degrees
        df["lon"] = ((-1) ** (df["LONDD"] < 0)) * (
            np.abs(df["LONDD"]) + df["LONMN"] / 60 + df["LONSS"] / 3600
        )
        df["lat"] = ((-1) ** (df["LATDD"] < 0)) * (
            np.abs(df["LATDD"]) + df["LATMN"] / 60 + df["LATSS"] / 3600
        )
        posBounds[file] = (df["datetime"].iloc[0], df["datetime"].iloc[-1])
        position[file] = df

    # Loop over hdf5 files and add solutions from appropriate pos file
    for h5 in hdf5:
        with h5py.File(h5, mode="r+") as fd:
            h5times = np.array(list(map(np.datetime64, fd["raw/gps0"]["utc"])))
            match = None
            for pos in posBounds.keys():
                bound = posBounds[pos]
                if h5times[0] > bound[0] and h5times[-1] < bound[1]:
                    match = pos
                    break
            if match is None:
                print("No matching pos file found for " + h5)

            # Add to file
            df = position[match]
            epoch = h5times[0]
            th5_sse = ((h5times - epoch).astype("timedelta64[us]")).astype(
                np.float64
            ) / 1e6
            tppp_sse = (
                (df["datetime"].to_numpy() - epoch).astype("timedelta64[us]")
            ).astype(
                np.float64
            ) / 1e6 - 18  # leap seconds... should do this better

            loni = np.interp(th5_sse, tppp_sse, df["lon"])
            lati = np.interp(th5_sse, tppp_sse, df["lat"])
            hgti = np.interp(th5_sse, tppp_sse, df["HGT(m)"])

            ppp_t = np.dtype(
                [("lon", "f8"), ("lat", "f8"), ("hgt", "f8"), ("utc", "S26")]
            )
            ppp = [None] * len(h5times)
            for i in range(len(h5times)):
                ppp[i] = tuple(
                    [
                        loni[i],
                        lati[i],
                        hgti[i],
                        h5times[i],
                    ]
                )
            ppp = np.array(ppp, dtype=ppp_t)

            drv = fd.require_group("drv")
            ppp0 = drv.require_dataset("ppp0", shape=ppp.shape, dtype=ppp.dtype)
            ppp0[:] = ppp
            ppp0.attrs["desc"] = "CSRS PPP solution"


main()
