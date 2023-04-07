#!/usr/bin/python3

# Plot 0.1 second of samples

import os
import matplotlib.pyplot as plt
import numpy as np

# Acquire samples
os.system(
    "/opt/uhd/host/build/examples/rx_samples_to_file --type short --rate 20e6 --duration 0.1 --file /home/radar/groundhog/data/tmp_plot.dat"
)

data = np.fromfile("/home/radar/groundhog/data/tmp_plot.dat", dtype=np.int16)[::2]
t = 1e6*np.arange(len(data)) / 20e6

plt.figure(figsize=(16, 8))
plt.plot((t, data, "k-")
plt.xlim(0, t[-1])
plt.xlabel("Time ($\mu$s)")
plt.show()

os.system("rm /home/radar/groundhog/data/tmp_plot.dat")
