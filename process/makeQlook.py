#!/usr/bin/python3

import argparse

import matplotlib.pyplot as plt
import h5py
import scipy.signal as sig
import numpy as np

import glob


def cli():
    # Command line interface
    parser = argparse.ArgumentParser(
        description="Generate quicklook of Groundhog HDF5 files"
    )
    parser.add_argument(
        "files",
        type=str,
        help="Groundhog HDF5 file(s) to generate quicklooks from",
        nargs="+",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()
    return args


def main():
    args = cli()

    for file in args.files:
        try:
            if args.verbose:
                print(file)

            with h5py.File(file, mode="r") as fd:
                rx = fd["raw/rx0"][:]
                fs = fd["raw/rx0"].attrs["fs"]
                pretrig = fd["raw/rx0"].attrs["pre_trig"]

            # Bandpass filter along traces
            flo = 0.5e6
            fhi = 8e6
            sos = sig.butter(8, [flo, fhi], btype="band", output="sos", fs=fs)
            rx = sig.sosfiltfilt(sos, rx, axis=0)

            # Filter accross traces - the filter edges are arbitrary here (units: fraction of nyquist), just played with it until I got a nice image
            sos = sig.butter(4, [0.0005, 0.01], btype="band", output="sos")
            rx = sig.sosfiltfilt(sos, rx, axis=1)

            # Remove mean trace
            # mt = np.mean(rx, axis=1)
            # rx = rx - mt[:, np.newaxis]

            # Gain
            gain = np.arange(rx.shape[0]) ** 2
            rx = rx * gain[:, np.newaxis]

            # Axes bounds
            t0 = -pretrig / fs
            t1 = (rx.shape[0] - pretrig) / fs
            c = 299792458
            cice = c / np.sqrt(3.15)
            z0 = t0 * cice / 2
            z1 = t1 * cice / 2

            # Red-blue image
            plt.figure(figsize=(8, 4))
            img = rx
            plt.imshow(
                img,
                aspect="auto",
                cmap="seismic",
                vmin=np.percentile(img, 2),
                vmax=np.percentile(img, 98),
                extent=[0, rx.shape[1], 1e6 * t1, 1e6 * t0],
            )

            plt.xlabel("Trace Index")
            plt.ylabel("Approx Two-Way Travel Time ($\\mu$s)")

            depthax = plt.gca().twinx()
            depthax.set_ylim(z1, z0)
            depthax.set_ylabel("Depth in ice (m)")

            plt.savefig(file.replace(".h5", "_rdbu.png"), dpi=200, bbox_inches="tight")
            plt.close()

            # Take envelope
            rx = sig.hilbert(rx, axis=0)
            rx = np.abs(rx)

            # Envelope image
            plt.figure(figsize=(8, 4))
            img = np.log10(np.abs(rx))
            plt.imshow(
                img,
                aspect="auto",
                cmap="Greys_r",
                vmin=np.percentile(img, 10),
                vmax=np.percentile(img, 99),
                extent=[0, rx.shape[1], 1e6 * t1, 1e6 * t0],
            )

            plt.xlabel("Trace Index")
            plt.ylabel("Approx Two-Way Travel Time ($\\mu$s)")

            depthax = plt.gca().twinx()
            depthax.set_ylim(z1, z0)
            depthax.set_ylabel("Depth in ice (m)")

            plt.savefig(file.replace(".h5", "_envl.png"), dpi=200, bbox_inches="tight")
            plt.close()
        except Exception as e:
            print(e)
            continue


main()
