# Generate SEG-Y files from raw Groundhog files
import argparse
import calendar
import glob
import os
import struct
import sys
import time

import h5py
import numpy as np
import pyproj


def cli():
    # Command line interface
    parser = argparse.ArgumentParser(
        description="Convert Groundhog digitizer files to HDF5"
    )
    parser.add_argument(
        "--dir",
        type=str,
        help="Directory of digitizer file(s) to convert to HDF5",
        default="/home/radar/groundhog/data",
    )
    args = parser.parse_args()
    return args


def parseHeader(data, file):
    if data[0:4] != b"\xef\xbe\xd0\xd0":
        print(
            file,
            "is improperly formed Groundhog digitizer file, missing header segment magic bytes.",
        )
        return -1

    header = {}

    header["spt"] = struct.unpack("q", data[4:12])[0]
    header["pre_trig"] = struct.unpack("q", data[12:20])[0]
    header["prf"] = struct.unpack("q", data[20:28])[0]
    header["stack"] = struct.unpack("q", data[28:36])[0]
    header["trig"] = struct.unpack("h", data[36:38])[0]
    header["fs"] = struct.unpack("d", data[38:46])[0]

    return header


def parseTraces(data, spt, file):
    partial = False
    bpt = 8 * spt + 26  # bytes per trace

    if data[0:4] != b"\xce\xfa\xed\xfe":
        print(
            file,
            "is improperly formed Groundhog digitizer file, missing data segment magic bytes.",
        )
        return -1, -1

    if data[-4:] != b"\xad\xde\xad\xde":
        print(
            file,
            "is improperly formed Groundhog digitizer file, missing file end magic bytes.",
        )
        print("Will continue attempt to convert")
        partial = True

    ntrace = (len(data) - 8) / bpt

    if ntrace != int(ntrace):
        if partial:
            nkeep = int(ntrace) * bpt + 4
            data = data[:nkeep]
        else:
            print("File appears corrupted (some partial traces missing)")
            print("Need to implement reader for this")
            return -1, -1

    ntrace = int(ntrace)
    rx = np.zeros((spt, ntrace), dtype=np.int64)
    times = []

    data = data[4:]
    for i in range(ntrace):
        times.append(data[i * bpt : i * bpt + 26].decode("utf-8"))
        rx[:, i] = struct.unpack("q" * spt, data[i * bpt + 26 : (i + 1) * bpt])

    return rx, times


def main():
    parser = argparse.ArgumentParser(
        description="Build a SEG-Y revision 2.0 formatted file from SHARAD USRDR PDS data and one from the accompanying surface clutter simulation, if supplied."
    )
    parser.add_argument("rgram", help="USRDR radargram (.img) file", type=str)
    parser.add_argument("geom", help="USRDR geometry (.tab) file", type=str)
    parser.add_argument(
        "--sim",
        "-s",
        metavar="sim",
        help="PDS sim (sim_lr.img) file",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--out",
        "-o",
        metavar="out",
        help="Output directory (default: ./)",
        type=str,
        default="./",
    )
    args = parser.parse_args()

    out = (
        args.out + "/" + args.rgram.split("/")[-1][:10]
    )  # Relies on PDS file naming convention (s_XXXXXXX_rgram.img)

    gensegy(args.rgram, args.geom, args.sim, out)

    return 0


def gensegy(header, rx, fix, file):
    ntrace = rx.shape[1]
    spt = rx.shape[0]

    # Build Segy 2.0 format files
    # https://seg.org/Portals/0/SEG/News%20and%20Resources/Technical%20Standards/seg_y_rev2_0-mar2017.pdf
    with open(file.replace(".dat", ".sgy"), "wb") as f:
        # Write 3200 byte text header
        f.write(build_txthead(os.path.basename(file)))

        # Write 400 byte binary header
        f.write(build_binhead(spt, ntrace, header["fs"]))

        # Convert to utm
        xform = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32607")

        x, y = xform.transform(fix[:, 1], fix[:, 0])
        print(x)
        print(y)
        print(fix)
        ### Write data traces
        for i in range(ntrace):
            f.write(build_trchead(spt, i + 1, x[i], y[i], header["fs"]))
            f.write(rx[:, i].astype(">f", order="C").tobytes(order="C"))

    return 0


def build_txthead(track):
    txthead = b""

    # (0) Track number string
    track = track[0:10]
    txthead += track.encode(encoding="ASCII", errors="strict")

    # (10) Rest of text header, 3200-10 = 3190 bytes
    for i in range(398):
        txthead += struct.pack("Q", 0)

    txthead += struct.pack("I", 0)
    txthead += struct.pack("H", 0)

    return txthead


def build_binhead(spt, ntrace, fs):
    ### Build binary header
    binhead = b""

    # (0) Job identification number
    binhead += struct.pack(">I", 1)
    # (4) Line number
    binhead += struct.pack(">I", 1)
    # (8) Reel number
    binhead += struct.pack(">I", 1)
    # (12) Traces per ensemble
    binhead += struct.pack(">H", 1)
    # (14) Auxiliary traces per ensemble
    binhead += struct.pack(">H", 0)
    # (16) Sample interval
    binhead += struct.pack(">H", int(1e12 / fs / 10))
    # (18) Field recording sample interval
    binhead += struct.pack(">H", int(1e12 / fs / 10))
    # (20) Samples per trace
    binhead += struct.pack(">H", spt)
    # (22) Field recording samples per trace
    binhead += struct.pack(">H", spt)
    # (24) Data format code
    binhead += struct.pack(">H", 5)
    # (26) Ensemble fold
    binhead += struct.pack(">H", 1)
    # (28) Trace sorting code
    binhead += struct.pack(">H", 4)
    # (30) Vertical sum code
    binhead += struct.pack(">H", 1)
    # (32) Sweep freq start
    binhead += struct.pack(">H", 0)
    # (34) Sweep freq end
    binhead += struct.pack(">H", 0)
    # (36) Sweep length
    binhead += struct.pack(">H", 0)
    # (38) Sweep type
    binhead += struct.pack(">H", 0)
    # (40) Trace number of sweep channel
    binhead += struct.pack(">H", 0)
    # (42) Sweep trace taper length at start
    binhead += struct.pack(">H", 0)
    # (44) Sweep trace taper length at end
    binhead += struct.pack(">H", 0)
    # (46) Taper type
    binhead += struct.pack(">H", 0)
    # (48) Correlated data traces, 2 is yes
    binhead += struct.pack(">H", 2)
    # (50) Binary gain recovered, 2 is no
    binhead += struct.pack(">H", 1)
    # (52) Amplitude recovery method, 1 is none
    binhead += struct.pack(">H", 4)
    # (54) Measurement system, 1 is meters
    binhead += struct.pack(">H", 1)
    # (56) Implulse signal polarity
    binhead += struct.pack(">H", 1)
    # (58) Vibratory polarity code
    binhead += struct.pack(">H", 0)
    # (60) Extended number of traces per ensemble
    binhead += struct.pack(">I", 0)
    # (64) Extended number of auxiliary traces per ensemble
    binhead += struct.pack(">I", 0)
    # (68) Extended samples per trace
    binhead += struct.pack(">I", 0)
    # (72) Extended sample interval
    binhead += struct.pack(">d", 37.5)
    # (80) Extended field recording sample interval
    binhead += struct.pack(">d", 0)
    # (88) Extended field recording samples per trace
    binhead += struct.pack(">I", 0)
    # (92) Extended ensemble fold
    binhead += struct.pack(">I", 0)
    # (96) An integer constant - see format doc
    binhead += struct.pack(">I", 16909060)
    # (100) 200 unassigned bytes
    for i in range(25):
        binhead += struct.pack("Q", 0)
    # (300) Major SEG-Y format revision number
    binhead += struct.pack(">B", 2)
    # (301) Minor SEG-Y format revision number
    binhead += struct.pack(">B", 0)
    # (302) Fixed length trace flag, 1 is yes - see format doc
    binhead += struct.pack(">H", 1)
    # (304) Number of extended text file headers
    binhead += struct.pack(">H", 0)
    # (306) Number of additional trace headers
    binhead += struct.pack(">I", 0)
    # (310) Time basis code, 4 is UTC
    binhead += struct.pack(">H", 4)
    # (312) Number of traces in file
    binhead += struct.pack(">Q", ntrace)
    # (320) Byte offset of first trace
    binhead += struct.pack(">Q", 0)
    # (328) Number of data trailer stanza records
    binhead += struct.pack(">I", 0)
    # (332) 68 unassigned bytes
    for i in range(17):
        binhead += struct.pack(">I", 0)

    return binhead


def build_trchead(spt, i, x, y, fs):
    # i - trace number
    trchead = b""
    # (0) Trace sequence number within line
    trchead += struct.pack(">I", i)
    # (4) Trace sequence number within file - starts at 1
    trchead += struct.pack(">I", i)
    # (8) Original field record number
    trchead += struct.pack(">I", i)
    # (12) Trace number in original field record
    trchead += struct.pack(">I", i)
    # (16) Energy source point number
    trchead += struct.pack(">I", 0)
    # (20) Ensemble number
    trchead += struct.pack(">I", i)
    # (24) Trace number within ensemble
    trchead += struct.pack(">I", 0)
    # (28) Trace ID code, 1 is time domain
    trchead += struct.pack(">H", 1)
    # (30) Number of vertically summed traces
    trchead += struct.pack(">H", 0)
    # (32) Number of horizontally stacked traces (stacking??)
    trchead += struct.pack(">H", 0)
    # (34) Data use, 1 is production
    trchead += struct.pack(">H", 1)
    # (36) Distance from center of source point to center of rx group
    trchead += struct.pack(">I", 0)
    # (40) Elevation of rx group
    trchead += struct.pack(">I", 0)
    # (44) Surface elevation at source location
    trchead += struct.pack(">I", 0)
    # (48) Source depth below surface
    trchead += struct.pack(">I", 0)
    # (52) Seismic datum elevation at rx group
    trchead += struct.pack(">I", 0)
    # (56) Seismic datum elevation at source
    trchead += struct.pack(">I", 0)
    # (60) Water column height at source location
    trchead += struct.pack(">I", 0)
    # (64) Water column height at rx group location
    trchead += struct.pack(">I", 0)
    # (68) Scalar to be applied to last seven fields for real val - see format doc
    trchead += struct.pack(">H", 1)
    # (70) Scalar to be applied to four following fields for real val - see format doc
    trchead += struct.pack(">h", 1)
    # (72) Source X coord
    trchead += struct.pack(">f", x)
    # (76) Source Y coord
    trchead += struct.pack(">f", y)
    # (80) rx group X coord
    trchead += struct.pack(">f", x)
    # (84) rx group Y coord
    trchead += struct.pack(">f", y)
    # (88) Coordinate units, 3 is decimal degrees
    trchead += struct.pack(">H", 1)
    # (90) Weathering velocity
    trchead += struct.pack(">H", 0)
    # (92) Subweathering velocity
    trchead += struct.pack(">H", 0)
    # (94) Uphole time at source in ms
    trchead += struct.pack(">H", 0)
    # (96) Uphole time at group in ms
    trchead += struct.pack(">H", 0)
    # (98) Source static correction in ms
    trchead += struct.pack(">H", 0)
    # (100) Group static correction in ms
    trchead += struct.pack(">H", 0)
    # (102) Total static correction applied in ms
    trchead += struct.pack(">H", 0)
    # (104) Lag time A
    trchead += struct.pack(">H", 0)
    # (106) Lag time B
    trchead += struct.pack(">H", 0)
    # (108) Delay recording time
    trchead += struct.pack(">H", 0)
    # (110) Mute time start in ms
    trchead += struct.pack(">H", 0)
    # (112) Mute time stop in ms
    trchead += struct.pack(">H", 0)
    # (114) Samples in this trace
    trchead += struct.pack(">H", spt)
    # (116) Sample interval for this trace
    trchead += struct.pack(">H", int(1e12 / fs / 10))
    # (118) Gain type of field instruments
    trchead += struct.pack(">H", 0)
    # (120) Instrument gain constant
    trchead += struct.pack(">H", 0)
    # (122) Instrument early or initial gain
    trchead += struct.pack(">H", 0)
    # (124) Correlated, 2 is yes
    trchead += struct.pack(">H", 2)
    # (126) Sweep freq start Hz
    trchead += struct.pack(">H", 0)
    # (128) Sweep freq end Hz
    trchead += struct.pack(">H", 0)
    # (130) Sweep length ms
    trchead += struct.pack(">H", 0)
    # (132) Sweep type, 1 is linear
    trchead += struct.pack(">H", 1)
    # (134) Sweep trace taper length start ms
    trchead += struct.pack(">H", 0)
    # (136) Sweep trace taper length end ms
    trchead += struct.pack(">H", 0)
    # (138) Taper type
    trchead += struct.pack(">H", 0)
    # (140) Alias filter freq Hz
    trchead += struct.pack(">H", 0)
    # (142) Alias filter slope
    trchead += struct.pack(">H", 0)
    # (144) Notch filter freq Hz
    trchead += struct.pack(">H", 0)
    # (146) Notch filter flope
    trchead += struct.pack(">H", 0)
    # (148) Low-cut freq Hz
    trchead += struct.pack(">H", 0)
    # (150) Hi-cut freq Hz
    trchead += struct.pack(">H", 0)
    # (152) Low-cut slope
    trchead += struct.pack(">H", 0)
    # (154) Hi-cut slope
    trchead += struct.pack(">H", 0)
    # (156) Year data recorded
    trchead += struct.pack(">H", 0)
    # (158) Day of year data recorded
    trchead += struct.pack(">H", 0)
    # (160) Hour of day
    trchead += struct.pack(">H", 0)
    # (162) Minute of hour
    trchead += struct.pack(">H", 0)
    # (164) Second of minute
    trchead += struct.pack(">H", 0)
    # (166) Time basis code
    trchead += struct.pack(">H", 0)
    # (168) Trace weighting factor
    trchead += struct.pack(">H", 0)
    # (170) Geophone group number of roll switch position one
    trchead += struct.pack(">H", 0)
    # (172) Geophone group number of trace number one within original field record
    trchead += struct.pack(">H", 0)
    # (174) Geophone group number of last trace within original field record
    trchead += struct.pack(">H", 0)
    # (176) Gap size
    trchead += struct.pack(">H", 0)
    # (178) Over travel assoc with taper at beginning of line
    trchead += struct.pack(">H", 0)
    # (180) Unused
    trchead += struct.pack(">H", 0)
    # (182) X coordinate of ensemble position of this trace
    trchead += struct.pack(">d", x)
    # (190)Y coordinate of ensemble position of this trace
    trchead += struct.pack(">d", y)
    # (198) 2 empty bytes
    trchead += struct.pack(">H", 0)
    # (200) 40 empty bytes
    for i in range(5):
        trchead += struct.pack(">Q", 0)

    return trchead


def DDMtoDD(ddm):
    d = np.float64(ddm[:-7])
    m = np.float64(ddm[-7:]) / 60.0
    return d + m


def parseGPS(file):
    try:
        nmeas = open(file, mode="r").read().splitlines()
    except Exception as e:
        print(e)
        return -1, -1

    gpgga = []
    gpzda = []
    tgpgga = []
    tgpgza = []
    for i, nmea in enumerate(nmeas):
        if "class" in nmea:
            # skip json info strings
            continue

        syst, fix = nmea.split("$", maxsplit=1)

        if "GPGGA" in fix:
            gpgga.append(fix)
            tgpgga.append(syst)

        if "GPZDA" in fix:
            gpzda.append(fix)
            tgpgza.append(syst)

    if len(gpgga) != len(gpzda):
        print("Number of GPGGA strings != number of GPZDA string, need to handle this")
        return -1, -1

    fix = np.zeros((len(gpgga), 4))  # lon, lat, hgt, utc
    for i in range(len(gpgga)):
        gga = gpgga[i].split(",")
        zda = gpzda[i].split(",")
        if gga[1] != zda[1]:
            print("GPGGA and GPZDA misalignment, need to handle this")
            return -1, -1

        fix[i, 1] = DDMtoDD(gga[2])
        fix[i, 0] = DDMtoDD(gga[4])
        fix[i, 2] = gga[9]

        if gga[3] == "S":
            fix[i, 1] *= -1

        if gga[5] == "W":
            fix[i, 0] *= -1

        # Convert UTC time to seconds of day
        fix[i, 3] = calendar.timegm(
            time.strptime(zda[4] + zda[3] + zda[2] + zda[1], "%Y%m%d%H%M%S.%f")
        )

    return tgpgga, fix


def interpFix(timesGps, timesFile, fix):
    # Reference everyting to first GPS time
    timesGps = np.array(
        [
            calendar.timegm(time.strptime(t.strip(), "%Y-%m-%d %H:%M:%S.%f:"))
            for t in timesGps
        ]
    )
    timesFile = np.array(
        [
            calendar.timegm(time.strptime(t.strip(), "%Y-%m-%dT%H:%M:%S.%f"))
            for t in timesFile
        ]
    )

    # Check for suspicious things
    if timesGps[0] > timesFile[0] or timesGps[-1] < timesFile[-1]:
        print("GPS times do not entirely contain data file times, proceed with caution")

    loni = np.interp(timesFile, timesGps, fix[:, 0])
    lati = np.interp(timesFile, timesGps, fix[:, 1])
    hgti = np.interp(timesFile, timesGps, fix[:, 2])
    timei = np.interp(timesFile, timesGps, fix[:, 3])

    return np.stack((loni, lati, hgti, timei)).T


def main():
    args = cli()
    files = glob.glob(args.dir + "/*.dat")

    if len(files) == 0:
        print("No data files found, exiting")

    for file in files:
        print("Converting " + file)
        try:
            fd = open(file, "rb")
        except Exception as e:
            print(e)
            continue

        data = fd.read()
        fd.close()

        if len(data) < 46:
            print(
                "Incomplete file, only partial header present -- skipping conversion\n"
            )
            continue

        header = parseHeader(data, file)

        if header == -1:
            print("Failed to parse file header\n")
            continue

        rx, timesFile = parseTraces(data[46:], header["spt"], file)

        if timesFile == -1:
            print("Failed to parse file data segment\n")
            continue

        gpsFile = file.replace(".dat", ".txt")
        timesGps, fix = parseGPS(gpsFile)

        if timesGps == -1:
            print(
                "No GPS file found or failed to parse GPS file -- skipping conversion\n"
            )
            continue

        fix = interpFix(timesGps, timesFile, fix)
        print(file)

        if gensegy(header, rx, fix, file) == -1:
            print("Faild to build SEG-Y\n")
            continue

        print()

    return 0


main()
