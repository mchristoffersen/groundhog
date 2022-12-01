import argparse
import rasterio as rio
import pyproj
import h5py
import numpy as np
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(
        description="Generate quicklook map products of Ruth Glacier data"
    )
    parser.add_argument("data", help="Data file(s)", nargs="+")
    parser.add_argument(
        "--base",
        "-b",
        help="Basemap",
        default="/home/mchristo/proj/field/Ruth2022/ifsar/USGS_AK5M_RUTH_HS_utm6n.tif",
    )
    args = parser.parse_args()

    print(args.base)

    navcrs = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"

    # Load basemap (Ruth area hillshade)
    bm = rio.open(args.base, "r")

    for file in args.data:
        # Load data file
        try:
            fd = h5py.File(file, "r")
        except OSError:
            continue

        # Calculate quicklook map bounds
        #try:
        #    gps0 = fd["fix0"]
        #    lat = [lat for (lat, lon, hgt) in gps0]
        #    lon = [lon for (lat, lon, hgt) in gps0]
        #except KeyError:
        try:
            gps0 = fd["/raw/rxFix0"]
        except KeyError:
            fd.close()
            continue
        lat = [lat for (lat, lon, hgt) in gps0]
        lon = [lon for (lat, lon, hgt) in gps0]

        # Fix decimal minutes oops
        #for i in range(len(lat)):
        #    lat[i] = lat[i]//1 + 100*(lat[i]%1)/60
        #    lon[i] = np.trunc(lon[i]) + 100*(lon[i]-np.trunc(lon[i]))/60

        transformer = pyproj.Transformer.from_crs(navcrs, bm.crs)

        try:
            x, y = transformer.transform(lon, lat)
        except pyproj.exceptions.ProjError:
            continue

        x = np.array(x)
        y = np.array(y)

        gt = ~bm.transform
        ix, iy = gt * (x, y)

        pad = 200
        bounds = [int(min(ix))-pad, int(max(ix))+pad, int(min(iy))-pad, int(max(iy))+pad]
        print(bounds)
        rowSub = (bounds[2], bounds[3] + 1)
        colSub = (bounds[0], bounds[1] + 1)

        try:
            win = rio.windows.Window.from_slices(rowSub, colSub)
        except rio.errors.WindowError:
            continue

        data = bm.read(1, window=win)

        lx, ly = bm.transform * (np.array(bounds[:2]), np.array(bounds[2:]))
        print("lims", lx, ly)

        #print(gt[2])
        #X = np.arange(bm.width)*gt[0]+gt[2]
        #Y = np.arange(bm.height)*gt[4]+gt[5]


        ix = ix-bounds[0]
        iy = iy-bounds[2]
        plt.imshow(data, cmap="Greys_r", extent=[lx[0]/1e3, lx[1]/1e3, ly[1]/1e3, ly[0]/1e3])
        plt.plot(x/1e3, y/1e3, 'r--')
        plt.plot(x[0]/1e3, y[0]/1e3, 'go')

        name = file.split("/")[-1].replace(".h5", ".png")
        plt.title(file.split("/")[-1])
        plt.xlabel("X (km)")
        plt.ylabel("Y (km)")
        plt.savefig("./map_qlook/" + name, dpi=200, bbox_inches="tight")
        plt.cla()

        #plt.imshow(data)
        #plt.plot(ix-bounds[0], iy-bounds[2])
        #plt.show()

    bm.close()


main()
