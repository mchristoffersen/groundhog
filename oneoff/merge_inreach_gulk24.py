# Merge 2024 Gulkana inreach
import argparse
import numpy as np
import h5py
import pandas as pd
import matplotlib.pyplot as plt
import os
#import matplotlib as mpl
#mpl.rcParams['axes.formatter.useoffset'] = False


def cli():
    # Command line interface
    parser = argparse.ArgumentParser(
        description="Merge 2024 Gulkana inreach tracking points"
    )
    parser.add_argument("hdf5", type=str, help="HDF5 Files", nargs="+")
    parser.add_argument("pos", type=str, help="InReach CSV", nargs="+")
    args = parser.parse_args()
    return args


def main():
    args = cli()

    # Sort hdf5 from pos files
    files = args.hdf5 + args.pos

    hdf5 = []
    position = None
    for file in files:
        if file.lower()[-3:] == ".h5":
            hdf5.append(file)
        elif file.lower()[-4:] == ".csv":
            position = file
        else:
            print("Unrecognized file " + file)

    # Load InReach CSV
    df = pd.read_csv(position)
    df["time"] = df["time"].apply(np.datetime64)

    # Loop over hdf5 files and add solutions from appropriate pos file
    for h5 in sorted(hdf5):
        with h5py.File(h5, mode="r+") as fd:
            skip = False
            try:
                h5times = np.array(list(map(np.datetime64, fd["raw/gps0"]["utc"])))
            except KeyError:
                print(h5, "has no /raw/gps0")
                continue

            if(h5times[0] < df["time"][0] or h5times[-1] > df["time"].iloc[-1]):
                print(h5, "not covered by InReach")
                continue

            # Add to file
            epoch = h5times[0]
            th5_sse = ((h5times - epoch).astype("timedelta64[us]")).astype(
                np.float64
            ) / 1e6
            tppp_sse = (
                (df["time"].to_numpy() - epoch).astype("timedelta64[us]")
            ).astype(np.float64) / 1e6 - 18 # leap seconds... should do this better

            loni = np.interp(th5_sse, tppp_sse, df["lon"])
            lati = np.interp(th5_sse, tppp_sse, df["lat"])
            hgti = np.interp(th5_sse, tppp_sse, df["ele"])

            #plt.plot(loni, lati)
            #plt.title(os.path.basename(h5))
            #plt.show()

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

            raw = fd.require_group("raw")
            ppp0 = raw.require_dataset(
                "ppp0", shape=ppp.shape, dtype=ppp.dtype
            )
            ppp0[:] = ppp
            ppp0.attrs["desc"] = "Position interpolated from 1 minute InReach tracking points - not actually PPP"


main()
