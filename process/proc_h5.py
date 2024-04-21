# Generate processed dataset from rx0 in Groundhog HDF files
import argparse
import h5py
import pyproj
import matplotlib.pyplot as plt
import numpy as np
import scipy


def cli():
    # Command line interface
    parser = argparse.ArgumentParser(
        description="Generate processed dataset from /raw/rx0 in Groundhog HDF5 files"
    )
    parser.add_argument("files", type=str, help="HDF5 files to process", nargs="+")
    args = parser.parse_args()
    return args


def main():
    args = cli()
    for file in args.files:
        with h5py.File(file, mode="r+") as fd:
            # Restack to constant intervals
            ppp0 = fd["drv/ppp0"][:]
            xform = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:4978")
            x, y, z = xform.transform(ppp0["lat"], ppp0["lon"], ppp0["hgt"])
            dist = np.append(
                0,
                np.cumsum(np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2 + np.diff(z) ** 2)),
            )

            ival = 2  # stacking interval (m)
            nrstk = np.ceil(dist[-1]/ival).astype(np.uint32)

            rx0 = fd["raw/rx0"]
            rstk = np.zeros((rx0.shape[0], nrstk), dtype=np.float64)
            ppp_rstk = np.empty(nrstk, ppp0.dtype)
            time = np.array(list(map(np.datetime64, ppp0["utc"])))
            epoch = time[0]
            time_sse = time - epoch

            for i in range(nrstk):
                mask = np.logical_and(dist >= ival*i, dist < ival*(i+1))
                rstk[:, i] = np.mean(rx0[:, mask], axis=1)
                ppp_rstk[i] = (
                    np.mean(ppp0["lon"][mask]),
                    np.mean(ppp0["lat"][mask]),
                    np.mean(ppp0["hgt"][mask]),
                    np.datetime_as_string(epoch + np.mean(time_sse[mask]))
                )

            restack = fd.require_group("restack")
            rx0 = restack.require_dataset(
                "rx0", shape=rstk.shape, dtype=rstk.dtype
            )
            rx0[:] = rstk
            rx0.attrs["desc"] = "Data from /raw/rx0 restacked to constant trace spacing (%dm)" % ival
            rx0.attrs["fs"] = fd["raw/rx0"].attrs["fs"]
            rx0.attrs["pre_trig"] = fd["raw/rx0"].attrs["pre_trig"]
            rx0.attrs["spt"] = fd["raw/rx0"].attrs["spt"]
            rx0.attrs["trig"] = fd["raw/rx0"].attrs["trig"]
            rx0.attrs["interval"] = 2

            # Add restacked gps
            ppp_rstk0 = restack.require_dataset(
                "ppp0", shape=ppp_rstk.shape, dtype=ppp_rstk.dtype
            )
            ppp_rstk0[:] = ppp_rstk
            ppp_rstk0.attrs["desc"] = "Mean CSRS PPP solution for each restacked trace"


main()
