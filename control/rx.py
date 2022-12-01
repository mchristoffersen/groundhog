import uhd
import numpy as np
import matplotlib.pyplot as plt
import signal
import multiprocessing
import h5py
import argparse
import os

# Define receive worker
def worker(q, usrp, stack, trig, trace_len, fs, pre_trig=32):
    # You don't listen to the keyboard    
    s = signal.signal(signal.SIGINT, signal.SIG_IGN)

    # High priority
    os.nice(-20)

    # Initialize HDF5 file
    # Find a unique file name
    i = 0
    base = "./groundhog_data_"
    fn = base+"%03d.h5" % i
    while os.path.isfile(fn):
        i += 1 
        fn = base+"%03d.h5" % i 

    print(fn)
    with h5py.File(fn, "x") as fd:
        rx0 = fd.create_dataset("rx0", (512, 10000), maxshape=(trace_len, None), dtype=np.float32, chunks=True)
        rx0.attrs["fs"] = fs
        rx0.attrs["trigger_threshold"] = trig
        rx0.attrs["pre_trigger"] = pre_trig
        rx0.attrs["stack"] = stack

        dt = np.dtype([("lat", "f4"), ("lon", "f4"), ("hgt", "f4"), ("time", "u8")])
        gps0 = fd.create_dataset('gps0', (10000,), maxshape=(None,), dtype=dt, chunks=True)

        # Trigger/stack/record
        # initialize last, crnt, next
        last = q.get()
        if(last[0] == "DIEDIEDIE"):
            # Close HDF5 file
            print("No data recorded $HDF5NAME")
            return 0
        last = last[1]

        crnt = q.get()
        if(crnt[0] == "DIEDIEDIE"):
            # Close HDF5 file
            print("No data recorded $HDF5NAME")
            return 0
        crnt = crnt[1]

        next = q.get()
        if(next[0] == "DIEDIEDIE"):
            # Close HDF5 file
            print("No data recorded $HDF5NAME")
            return 0
        next = next[1]  

        trace = np.zeros(trace_len, dtype=np.float32)
        num_stacks = 0
        num_trace = 0

        # Buffer length
        bufsize = len(last)

        # Initialize real time trace plot
        plt.ion()
        fig = plt.figure()
        ax = fig.add_subplot(111)
        x = np.arange(512)
        y = np.zeros(512)
        line1, = ax.plot(1e6*x*1/20e6, y)
        yflag = True

        while True:
            # TODO: think about scenario where only tail end of impulse
            # is captured in crnt, so there is a bit of misalignment in the
            # stacking of that pulse.
            # Won't really matter but still technically a bug.
            
            # Make "supr" array last + crnt + next
            supr = np.concatenate((last, crnt, next))

            # Look for triggers in crnt
            crnt_trig = crnt >= trig
            trig_loc = np.argmax(crnt_trig)

            while trig_loc != 0 or crnt_trig[0]:
                #print("Trigger at %d" % trig_loc)
                #print("Trace from %d to %d" % (trig_loc-pre_trig, trig_loc+trace_len-pre_trig))
                trace = trace + supr[bufsize+trig_loc-pre_trig: bufsize+trig_loc+trace_len-pre_trig]  # Grab trace
                # Blank out trigger detection over duration of trace in crnt
                #print("Blanking trigs from %d to %d" % (max(trig_loc-pre_trig, 0), min(trig_loc+trace_len-pre_trig, bufsize)))
                crnt_trig[max(trig_loc-pre_trig, 0):min(trig_loc+trace_len-pre_trig, bufsize)] = False
                num_stacks += 1

                # Save trace if enough stacks have been done
                if num_stacks == stack:
                    # Save trace
                    # Add space if needed
                    if(num_trace >= rx0.shape[1]):
                        rx0.resize(rx0.shape[1] + 10000, axis=1)
                        gps0.resize(gps0.shape[0] + 10000)

                    rx0[:,num_trace] = trace
                 
                    # Update plot
                    line1.set_ydata(trace)
                    if(yflag):
                        ax.set_ylim(1.1*np.min(trace), 1.1*np.max(trace))
                        yflag = False
                    fig.canvas.draw()
                    fig.canvas.flush_events()
       
                    # Reset trace and stacking
                    trace[:] = 0
                    num_stacks = 0

                    # Add GPS loc
                    # Northern hemisphere and western hemisphere baked in here...
                    # not great, but I'm short on time.
                    try:
                        nmea = str(usrp.get_mboard_sensor("gps_gpgga"))
                        nmea = nmea.split(":")[1].split(",")
                        lat = float(nmea[2])/100
                        lon = -1*float(nmea[4])/100
                        hgt = float(nmea[9])
                    
                        time = str(usrp.get_mboard_sensor("gps_time"))
                        time = int(time.split(":")[1].split("sec")[0])
                
                        gps0[num_trace] = (lat, lon, hgt, time)
                    except Exception as e:
                        print(e)
                        gps0[num_trace] = (0,0,0,0)
                        break
                    
                    num_trace += 1                           
               

                # Look for another trigger
                trig_loc = np.argmax(crnt_trig)

            # Bump crnt->last and next->crnt then get new next
            last = crnt[:]
            crnt = next[:]
            next = q.get()
            #if(q.qsize() > 20):
            #    print("Queue size: %d" % q.qsize())
            if(next[0] == "DIEDIEDIE"):
                print("Death received")
                break
            next = next[1]
        
        # Clean up
        rx0.resize(num_trace, axis=1)
        gps0.resize(num_trace, axis=0)
        fd.close()

    print("Goodbye ( •̀ω•́ )")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Impulse radar receiver")
    parser.add_argument(
        "--stack",
        "-s",
        type=int,
        default=10000,
        help="how many pulses to stack (default = 10k)",
    )
    parser.add_argument(
        "--trace_length",
        "-l",
        type=int,
        default=512,
        help="Samples in each trace (default = 512)",
    )
    parser.add_argument(
        "--trigger",
        "-t",
        type=float,
        default=0.005,
        help="Trigger threshold (default = 0.005v)",
    )

    args = parser.parse_args()

    # High priority
    os.nice(-20)

    # Set up USRP

    usrp = uhd.usrp.MultiUSRP()

    center_freq = 0  # Hz
    sample_rate = 20e6  # Hz
    gain = 0  # dB

    usrp.set_rx_rate(sample_rate, 0)
    usrp.set_rx_freq(uhd.libpyuhd.types.tune_request(center_freq), 0)
    usrp.set_rx_gain(gain, 0)
    usrp.set_rx_antenna("A", 0)

    # Set up the streamer and receive buffer
    st_args = uhd.usrp.StreamArgs("fc32", "sc16")
    st_args.channels = [0]
    metadata = uhd.types.RXMetadata()
    streamer = usrp.get_rx_stream(st_args)
    recv_buffer = np.zeros((1, 10000), dtype=np.complex64)

    # Start rx worker
    queue = multiprocessing.Queue()
    p = multiprocessing.Process(
        target=worker, args=(queue, usrp, args.stack, args.trigger, args.trace_length, sample_rate)
    )
    p.start()

    # Start Stream
    stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
    stream_cmd.stream_now = True
    streamer.issue_stream_cmd(stream_cmd)

    # Receive Samples
    print("BEGIN RX... PRESS CTRL+C TO STOP")

    try:    
        while True:
            streamer.recv(recv_buffer, metadata)
            # Puke samples to queue
            queue.put(("samps", np.real(recv_buffer[0,:])))
    except (KeyboardInterrupt, RuntimeError):
        pass

    # Kill worker
    queue.put(("DIEDIEDIE", 0))
    print("Death delivered")
    queue.close()

    # Stop Stream
    try:
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        streamer.issue_stream_cmd(stream_cmd)
    except Exception as e:
        print(e)

    # Close out queue and process
    queue.join_thread()
    p.join()


main()
