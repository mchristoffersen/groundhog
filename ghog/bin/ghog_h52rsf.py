# Convert processed Ruth glacier radar data to RSF format
import argparse
import datetime
import getpass
import os
import socket

import h5py
import matplotlib.pyplot as plt
import numpy as np


def cli():
    parser = argparse.ArgumentParser(
        description="Convert Ruth Glacier HDF5 radar data file(s) to RSF"
    )
    parser.add_argument("files", nargs="+", help="file(s) to convert")

    return parser.parse_args()


def h52rsf(file):
    rsf = file.replace(".h5", ".rsf")

    with h5py.File(file, mode="r") as fd:
        dx = int(fd["/restack/rx0"].attrs["stack_interval"])
        pt = fd["/raw/rx0"].attrs["pre_trig"]
        # rx0 = fd["/restack/rx0"][pt:,:]  # should probably deal with pre-trigger samples
        rx0 = fd["/restack/rx0"][:]
        dt = 1.0 / fd["/raw/rx0"].attrs["fs"]

    # Band-limited interpolation (necessary for RTM, not needed for stolt)
    # RX0 = np.fft.rfft(rx0, axis=0)
    # npad = (RX0.shape[0]-1)*9
    # RX0 = np.pad(RX0, ((0, npad), (0,0)))
    # rx0pd = np.fft.irfft(RX0, axis=0)
    # dt = dt/10
    rx0pd = rx0

    with open(rsf, mode="x") as fd:
        # Write RSF header
        now = datetime.datetime.now()
        dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
        fd.write(
            "4.0\tsfrimfaxread\t%s:\t%s@%s\t%s\n\n"
            % (os.getcwd(), getpass.getuser(), socket.gethostname(), dt_string)
        )
        fd.write('\tin="stdin"\n')
        fd.write('\tdata_format="native_float"\n')
        fd.write("\tesize=4\n")
        fd.write('\tlabel1="Time"\n')
        fd.write('\tunit1="ns"\n')
        fd.write("\tn1=%d\n\to1=0\n\td1=%.9f\n" % (rx0pd.shape[0], dt * 1e9))
        fd.write('\tlabel2="Distance"\n')
        fd.write('\tunit2="m"\n')
        fd.write("\tn2=%d\n\to2=0\n\td2=%2.2f\n" % (rx0pd.shape[1], dx))
        fd.write("\n\f\f\x04")  # nl ff ff eot

        fd.close()

        # Write data
        fd = open(rsf, mode="ab")
        rx0pd.T.astype(np.float32).tofile(fd)
        fd.close()


def main():
    args = cli()

    for file in args.files:
        print("Converting: %s" % file)
        h52rsf(file)


main()
