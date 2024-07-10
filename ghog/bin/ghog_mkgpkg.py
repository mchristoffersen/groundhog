# Generate a geopackage containing the observation tracks for a given year
import sys, os, h5py
from datetime import datetime
import geopandas as gpd
from shapely.geometry import LineString
import argparse


def cli():
    parser = argparse.ArgumentParser(
        description="Generate Geopackage containing trajectories from Groundhog HDF5 files."
    )
    parser.add_argument("files", type=str, nargs="+", help="HDF5 file(s)")
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="./trajectories.gpkg",
        help="Output Geopackage file (default = ./trajectories.gpkg)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    return parser


def main():
    args = cli().parse_args()

    rows = []
    for file in args.files:
        if file.endswith(".h5"):
            if args.verbose:
                print(path)

            row = {}

            with h5py.File(file, "r") as fd:
                if "gps0" not in fd["raw"].keys():
                    print("No /raw/gps0 dataset found in %s" % file)
                    continue

                gps0 = fd["raw/gps0"][:]

            if len(gps0) == 0:
                print("No data in /raw/gps0 dataset in %s" % file)
                continue

            gps0 = [(lon, lat, elev) for (lon, lat, elev, time) in gps0]

            row["geometry"] = LineString(gps0)
            row["fname"] = os.path.basename(file)

            rows.append(row)

    gdf = gpd.GeoDataFrame(rows)
    gdf.crs = "EPSG:4326"
    gdf.set_geometry("geometry")
    gdf.to_file(args.output, layer="groundhog", driver="GPKG")


if __name__ == "__main__":
    main()
