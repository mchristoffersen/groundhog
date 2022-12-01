import sys
import h5py
from datetime import datetime
import numpy as np
import matplotlib.pyplot as plt
import pyproj
import argparse


def main():
    parser = argparse.ArgumentParser(description='Print out groundhog file information.')
    parser.add_argument('files', nargs='+',
                        help='HDF5 files to analyze')

    args = parser.parse_args()

    print("orig_name, proc_name, prf, geom, notes")

    for file in args.files:
        analyze(file)


def analyze(file):
    orig_name = file.split("/")[-1].replace(".h5", "")

    note = ""

    fix = True

    try:
        fd  = h5py.File(file, "r")
    except OSError:
        print("%s, , , , corrupt" % orig_name)
        return 0

    if(len(fd["gps0"]) < 10):
        print("%s, , , , short file" % orig_name)
        return 0

    i = 0
    t = datetime.utcfromtimestamp(fd["gps0"][i][3])
    ref = datetime.strptime("2022", "%Y")
    while t < ref:
        i += 1
        t = datetime.utcfromtimestamp(fd["gps0"][i][3])

    fd.close()

    proc_name = "./proc/" + datetime.strftime(t, "%Y%m%d_%H%M%S") + ".h5"

    try:
        fd = h5py.File(proc_name, 'r')
    except OSError:
        print("%s, , , , not processed" % orig_name)
        return 0

    prf = fd["/raw/rx0"].attrs["stack"]
    dist = fd["/raw/sep"][:]

    fd.close()

    if(np.any(dist > 200)):
        geom = "Moveout"
    else:
        geom = "Common offset"

    proc_name = proc_name.split('/')[-1].replace(".h5", "")
    print("%s, %s, %d, %s, " % (orig_name, proc_name, prf, geom))


main()