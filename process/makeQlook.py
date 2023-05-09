#!/usr/bin/python3

import argparse

import matplotlib.pyplot as plt
import h5py
import scipy.signal as sig
import numpy as np

import glob


def cli():
    # Command line interface
    parser = argparse.ArgumentParser(description="Generate quicklook of Groundhog data")

    parser.add_argument(
        "--dir",
        type=str,
        help="Directory of groundhog HDF5 file(s) to generate quicklooks from",
        default="/home/radar/groundhog/data",
    )
    args = parser.parse_args()
    return args


def main():
    args = cli()

    if(len(glob.glob(args.dir + "/*.h5")) == 0):
        print("No files found, exiting")
        return 1

    for file in glob.glob(args.dir + "/*.h5"):
        try:
            print(file)
            fd = h5py.File(file)
            rx = fd["raw"]["rx0"][:]
            fs = fd["raw"].attrs["fs"]
            fd = h5py.File(file)

            # Bandpass filter
            flo = 0.5e6
            fhi = 8e6
            sos = sig.butter(8, [flo, fhi], btype="band", output="sos", fs=fs)
            rx = sig.sosfiltfilt(sos, rx, axis=0)

            # Remove mean trace
            mt = np.mean(rx, axis=1)
            rx = rx - mt[:, np.newaxis]

            # Red-blue image
            plt.figure(figsize=(8, 4))
            plt.imshow(
                rx,
                aspect="auto",
                cmap="seismic",
                vmin=-np.std(rx) * 0.5,
                vmax=np.std(rx) * 0.5,
                extent=[0, rx.shape[1], 1e6 * rx.shape[0] / fs, 0],
            )
            plt.xlabel("Trace Index")
            plt.ylabel("Approx Two-Way Travel Time ($\mu$s)")
            plt.savefig(file.replace(".h5", "_rdbu.png"), dpi=200, bbox_inches="tight")

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
                vmin=np.percentile(img, 30),
                vmax=np.percentile(img, 99),
                extent=[0, rx.shape[1], 1e6 * rx.shape[0] / fs, 0],
            )
            plt.xlabel("Trace Index")
            plt.ylabel("Approx Two-Way Travel Time ($\mu$s)")
            plt.savefig(file.replace(".h5", "_envl.png"), dpi=200, bbox_inches="tight")
        except Exception as e:
            print(e)
            continue


main()
