import h5py
import sys
import numpy as np
import scipy.signal as signal
import matplotlib.pyplot as plt


fd = h5py.File(sys.argv[1], "r")

fs = fd["rx0"].attrs["fs"]
dt = 1/fs

rx0 = fd["rx0"]

t0 = -32*dt
t1 = (512-32)*dt

d0 = 1.7e8*t0/2
d1 = 1.7e8*t1/2

## Band pass filter ##
sos = signal.butter(4, [0.8e6, 8.5e6], btype="band", fs=fs, output="sos")
rx0 = signal.sosfiltfilt(sos, rx0, axis=0)

img = np.log(np.abs(signal.hilbert(rx0, axis=0))+0.001)
plt.figure()
plt.imshow(img, cmap="Greys_r", aspect="auto", extent=[0, rx0.shape[1], d1, d0], vmin=np.percentile(img, 20), vmax=np.percentile(img, 99.9))
plt.ylabel("Ice depth (m)")
plt.xlabel("Trace Index")
plt.show()