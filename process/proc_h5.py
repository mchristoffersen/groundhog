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
            # NMO correction
            sep = 50
            v = 1.7e8
            rx0 = fd["raw/rx0"]
            rx0nmo = np.zeros_like(rx0)
            dt = 1/rx0.attrs["fs"]
            t0 = (np.arange(rx0.shape[0])-rx0.attrs["pre_trig"])*dt
            t = np.sqrt(t0**2 + sep**2/v**2)
            for i in range(rx0.shape[1]):
                rx0nmo[:, i] = np.interp(t, t0, rx0[:, i])

            # Restack to constant intervals
            ppp = False
            try:
                pos = fd["drv/ppp0"][:]
                xform = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:4978")
                x, y, z = xform.transform(pos["lat"], pos["lon"], pos["hgt"])
                dist = np.append(
                    0,
                    np.cumsum(np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2 + np.diff(z) ** 2)),
                )
                ppp = True
            except KeyError:
                try:
                    pos = fd["raw/gps0"]
                except KeyError:
                    continue

                if(np.mean(pos["lon"]) == 0):
                    continue
                xform = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:4978")
                x, y, z = xform.transform(pos["lat"], pos["lon"], pos["hgt"])
                steps = np.sqrt(np.diff(x) ** 2 + np.diff(y) ** 2 + np.diff(z) ** 2)
                cutoff = 0.05
                steps[steps < 0.05] = 0
                dist = np.append(
                    0,
                    np.cumsum(steps),
                )

            ival = 5  # stacking interval (m)
            nrstk = np.ceil(dist[-1]/ival).astype(np.uint32)

            rstk = np.zeros((rx0.shape[0], nrstk), dtype=np.float64)
            pos_rstk = np.empty(nrstk, pos.dtype)

            time = np.array(list(map(np.datetime64, pos["utc"])))
            epoch = time[0]
            time_sse = time - epoch

            for i in range(nrstk):
                mask = np.logical_and(dist >= ival*i, dist < ival*(i+1))
                rstk[:, i] = np.mean(rx0nmo[:, mask], axis=1)
                pos_rstk[i] = (
                    np.mean(pos["lon"][mask]),
                    np.mean(pos["lat"][mask]),
                    np.mean(pos["hgt"][mask]),
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
            rx0.attrs["interval"] = ival

            # Add restacked gps
            if(ppp):
                pos_rstk0 = restack.require_dataset(
                    "ppp0", shape=pos_rstk.shape, dtype=pos_rstk.dtype
                )
                pos_rstk0.attrs["desc"] = "Mean CSRS PPP solution for each restacked trace"
            else:
                pos_rstk0 = restack.require_dataset(
                    "gps0", shape=pos_rstk.shape, dtype=pos_rstk.dtype
                )
                pos_rstk0.attrs["desc"] = "On-board gps solution for each restacked trace"
            pos_rstk0[:] = pos_rstk


main()
