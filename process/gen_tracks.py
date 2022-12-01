# Generate a geopackage containing the observation tracks for a given year
import sys, os, h5py
from datetime import datetime
import geopandas as gpd
from shapely.geometry import LineString
import argparse
import numpy as np


def main():
    # Maybe just loop over all files in here so ingest is not redone for each
    # Or seperate ingester and make intermediate product to use
    parser = argparse.ArgumentParser(
        description="Generate geopackage with tracks of Ruth Glacier data"
    )
    parser.add_argument("data", help="Data file(s)", nargs="+")
    parser.add_argument("--output", "-o", help="Output file", default="tracks.gpkg")
    args = parser.parse_args()

    gdf = gpd.GeoDataFrame(
        geometry=[],
        columns=[
            "fname",
        ],
    )
    gdf.crs = "EPSG:4326"
    for file in args.data:
        print(file)
        row = {}

        try:
            fd = h5py.File(file, "r")
        except OSError:
            continue

        try:
            fix0 = fd["/raw/rxFix0"]
        except KeyError:
            continue


        fix0 = [(lon, lat, hgt) for (lat, lon, hgt) in fix0]

        #for i, pos in enumerate(fix0):
        #    lon = np.trunc(pos[0]) + 100*(pos[0]-np.trunc(pos[0]))/60
        #    lat = pos[1]//1 + ((pos[1]%1)*100)/60
        #    fix0[i] = (lon, lat, pos[2])

        #print(gps0)

        row["geometry"] = LineString(fix0)

        row["fname"] = file.split("/")[-1]

        fd.close()

        gdf = gdf.append(row, ignore_index=True)

    gdf.to_file(args.output, layer="tracks", driver="GPKG")


main()
