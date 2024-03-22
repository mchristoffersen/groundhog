#!/usr/bin/python3

# Plot 0.1 second of samples

import os
import matplotlib.pyplot as plt
import numpy as np

tmpfile = "/home/groundhog/groundhog/data/tmp_plot.dat"

# Acquire samples
os.system(
    "/usr/local/lib/uhd/examples/rx_samples_to_file --type short --rate 25e6 --duration 0.1 --file " + tmpfile
)

data = np.fromfile(tmpfile, dtype=np.int16)[::2]
data = data[100:]

t = 1e6*np.arange(len(data)) / 25e6

plt.figure(figsize=(16, 8))
plt.plot(t, data, "k-")
plt.xlim(0, 5000)
plt.xlabel("Time ($\mu$s)")
plt.yticks(fontsize=20, weight="bold")
plt.title("PRESS [ENTER] TO CLOSE")
plt.draw()
plt.waitforbuttonpress(0)
plt.close()
os.system("rm " + tmpfile)
