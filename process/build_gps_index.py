import glob
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


def makedd(df):
    # Make decimal degrees from a NRCAN PPP solution dataframe
    neg = df["latdd"] < 0
    df["lat"] = ((-1)**neg)*(np.abs(df["latdd"]) + df["latmn"]/60 + df["latss"]/3600)

    neg = df["londd"] < 0
    df["lon"] = ((-1)**neg)*(np.abs(df["londd"]) + df["lonmn"]/60 + df["lonss"]/3600)

    return df


def main():
    files = glob.glob("./gps/ppp/*.pos")
    tx_indx = "./gps/ppp/tx_indx.txt"
    rx_indx = "./gps/ppp/rx_indx.txt"

    tx = open(tx_indx, "w")
    rx = open(rx_indx, "w")

    for file in files:
        cols = [
            "dir",
            "frame",
            "stn",
            "doy",
            "date",
            "time",
            "nsat",
            "gdop",
            "rmsc",
            "rmsp",
            "dlat",
            "dlon",
            "dhgt",
            "sdlat",
            "sdlon",
            "sdhgt",
            "latdd",
            "latmn",
            "latss",
            "londd",
            "lonmn",
            "lonss",
            "hgt",
            "utm_zone",
            "utm_east",
            "utm_north",
            "utm_sclpnt",
            "utm_sclcbn",
        ]
        # cols = ["date", "time", "latitude", "longitude", "height", "Q", "ns", "sdn", "sde", "sdu", "sdne", "sdeu", "sdun", "age", "ratio"]
        df = pd.read_csv(file, skiprows=6, names=cols, delim_whitespace=True)
        df = makedd(df)
        t0 = df["date"][0] + "T" + df["time"][0]
        t1 = df["date"][len(df) - 1] + "T" + df["time"][len(df) - 1]

        if "SCOOBY" in file:
            rx.write("%s,%s,%s\n" % (file, t0, t1))
        elif "DOOOO" in file:
            tx.write("%s,%s,%s\n" % (file, t0, t1))

    tx.close()
    rx.close()


main()
