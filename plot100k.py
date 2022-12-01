import uhd
import matplotlib.pyplot as plt
import numpy as np

usrp = uhd.usrp.MultiUSRP()
samples = usrp.recv_num_samps(100000, 0, 20e6, [0], 0)[0]

plt.plot(np.real(samples))
plt.show()
