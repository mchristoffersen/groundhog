# Make quicklook images from Groundhog HDF5 files
import argparse
import glob

import h5py
import matplotlib.pyplot as plt
import numpy as np
import scipy.signal as sig

import ghog


def cli():
    # Command line interface
    parser = argparse.ArgumentParser(
        description="Generate quicklook figures of Groundhog HDF5 files."
    )
    parser.add_argument(
        "files",
        type=str,
        help="Groundhog HDF5 file(s) to generate quicklooks from.",
        nargs="+",
    )
    parser.add_argument(
        "-g",
        "--group",
        type=str,
        default="raw",
        help="Group to load from HDF5 file (default = raw).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    return parser


def main():
    args = cli().parse_args()

    if args.verbose:
        print("Generating figure from:")

    for file in args.files:
        if not file.endswith(".h5"):
            print("\t%s does not have .h5 extension, skipping" % file)
            continue

        if args.verbose:
            print("\t%s" % file)

        data = ghog.load(file, group=args.group)

        # Bandpass filter traces
        data = ghog.filt(data, (0.5e6, 5e6), axis=0)

        # Make figure
        ghog.figure(data, file=file.replace(".h5", ".png"), tpow=2, pclip=3)


if __name__ == "__main__":
    main()
