# Generate a geopackage containing the observation tracks for a given year
import argparse
import os
import sys
from datetime import datetime

import geopandas as gpd
import h5py
from shapely.geometry import LineString

import ghog


def cli():
    parser = argparse.ArgumentParser(
        description="Generate Geopackage containing trajectories from Groundhog HDF5 files."
    )
    parser.add_argument("files", type=str, nargs="+", help="Groundhog HDF5 file(s)")
    parser.add_argument(
        "-g",
        "--group",
        type=str,
        default="raw",
        help="Group to load from HDF5 file (default = raw)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="ghog_tracks.gpkg",
        help="Output Geopackage file (default = ghog_tracks.gpkg)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    return parser


def main():
    args = cli().parse_args()

    if args.verbose:
        print("Reading /%s/gps0 dataset from:" % (args.group))

    rows = []
    for file in args.files:
        if not file.endswith(".h5"):
            print("\t%s does not have .h5 extension, skipping" % file)
            continue

        if file.endswith(".h5"):
            if args.verbose:
                print("\t%s" % file)

            row = {}

            data = ghog.load(file, group=args.group)

            if len(data["gps"]) <= 1:
                print("Length 0 or 1 /%s/gps0 dataset in %s" % (args.group, file))
                continue

            gps = [(lon, lat, elev) for (lon, lat, elev, time) in data["gps"]]

            row["geometry"] = LineString(gps)
            row["fname"] = os.path.basename(file)

            rows.append(row)

    gdf = gpd.GeoDataFrame(rows)
    gdf.crs = "EPSG:4326"
    gdf.set_geometry("geometry")

    if args.verbose:
        print("Writing Geopackage to \n\t%s" % (args.output))
    gdf.to_file(args.output, layer="groundhog", driver="GPKG")


if __name__ == "__main__":
    main()
