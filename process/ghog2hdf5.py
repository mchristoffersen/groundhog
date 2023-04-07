import struct
import argparse
import os

import numpy as np
import h5py
import matplotlib.pyplot as plt


def cli():
    # Command line interface
    parser = argparse.ArgumentParser(description='Convert Groundhog digitizer files to HDF5')
    parser.add_argument('files', type=str, nargs="+",
                        help='Groundhog digitizer file(s) to convert to HDF5')
    args = parser.parse_args()
    return args


def parseHeader(data, file):
    if(data[0:4] != b'\xef\xbe\xd0\xd0'):
        print(file, "is improperly formed Groundhog digitizer file, missing header segment magic bytes.")
        return -1

    header = {}

    header["spt"] = struct.unpack('q', data[4:12])[0]
    header["pre_trig"] = struct.unpack('q', data[12:20])[0]
    header["prf"] = struct.unpack('q', data[20:28])[0]
    header["stack"] = struct.unpack('q', data[28:36])[0]
    header["trig"] = struct.unpack('h', data[36:38])[0]
    header["fs"] = struct.unpack('d', data[38:46])[0]

    return header


def parseTraces(data, spt, file):
    partial = False
    bpt = (8*spt + 19) # bytes per trace

    if(data[0:4] != b'\xce\xfa\xed\xfe'):
        print(file, "is improperly formed Groundhog digitizer file, missing data segment magic bytes.")
        return -1, -1

    if(data[-4:] != b'\xad\xde\xad\xde'):
        print(file, "is improperly formed Groundhog digitizer file, missing file end magic bytes.")
        print("Will continue attempt to convert")
        partial = True

    ntrace = (len(data)-8)/bpt
    
    if(ntrace != int(ntrace)):
        if(partial):
            nkeep = int(ntrace)*bpt + 4
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
        times.append(data[i*bpt: i*bpt+19].decode("utf-8"))
        rx[:, i] = struct.unpack('q'*spt, data[i*bpt+19: (i+1)*bpt])

    return rx, times


def buildH5(header, rx, times, file):
    outfile = os.path.dirname(file) + "/" + times[0].replace(":", "-") + ".h5"
    print("Saving ", outfile)

    fd = h5py.File(outfile, 'w')

    raw = fd.create_group("raw")
    raw.create_dataset("rx", data=rx)
    raw.create_dataset("time", data=times)

    for k, v in header.items():
        raw.attrs[k] = v

    fd.close()

    return 0


def main():
    args = cli()
    for file in args.files:
        print("Converting " + file)
        try:
            fd = open(file, 'rb')
        except Exception as e:
            print(e)
            continue

        data = fd.read()
        fd.close()

        if(len(data) < 46):
            print("Incomplete file, only partial header present")
            return 1

        header = parseHeader(data, file)

        if(header == -1):
            print("Failed to parse file header")
            return 1

        rx, times = parseTraces(data[46:], header["spt"], file)

        if(times == -1):
            print("Failed to parse file data segment")
            return 1

        if(buildH5(header, rx, times, file) == -1):
            print("Faild to build HDF5")
            return 1

    return 0


main()

cmt ="""
# Define a a warning message in case file is incomplete
message = "Couldn't find DEADEAD - file is incomplete - last trace dumped OwO"

with open(args.filename, 'rb') as f:
    # Initialize the host arrays for dates and traces
    traces = []
    dates = []

    # Read the header values
    data = f.read()
    ld = len(data)
    spt = struct.unpack('q', data[4:12])
    pre_trigger_samples = struct.unpack('q', data[12:20])
    prf = struct.unpack('q', data[20:28])
    stacking = struct.unpack('q', data[28:36])
    trigger_threshold = struct.unpack('h', data[36:38])
    sampling_frequency = struct.unpack('d', data[38:46])

    # Append the first date, for the first trace
    dates.append([data[50:69]])

    # The first trace starts at data[69]
    i = 69

    # Iterate so we grab each trace and their dates
    while i < len(data):
        # Select every byte between i and i + length of trace, and unpack them as int64 (8bytes for one integer)
        traces.append([struct.unpack('q', data[c:c+8]) for c in range(i,i+spt[0]*8-8,8)])
        # Append the dates
        dates.append([data[i+spt[0]*8:i+spt[0]*8+19]])
        # Update the iterator by adding the length of a trace + 19 bytes, the length of the date headers
        i += spt[0]*8+19
    
    # Verify the file is complete. If not, we get rid of the last trace
    if dates[-1][0] != b'\xad\xde\xad\xde':
        dates = dates[:-1]
        traces = traces[:-1]
        # Raise a warning
        warnings.warn(message, Warning)

    # Get rid of deadead and convert dates to strings
    dates = [dates[i][0].decode() for i in range(len(dates)-1)]
    
    # Convert to hdf5
    with h5py.File(f'traces_{dates[0].replace(":","-")}.h5', 'w') as f:
        # Create a dataset for the dates
        f.create_dataset('dates', data=dates)
        # Create a dataset for the traces
        f.create_dataset('traces', data=traces)
        
        # Create attributes for the header values
        f.attrs['ld'] = ld
        f.attrs['spt'] = spt
        f.attrs['pre_trigger_samples'] = pre_trigger_samples
        f.attrs['prf'] = prf
        f.attrs['stacking'] = stacking
        f.attrs['trigger_threshold'] = trigger_threshold
        f.attrs['sampling_frequency'] = sampling_frequency
        f.close()"""