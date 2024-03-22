#!/usr/bin/python3

# Return new filename (without file extension)

import os
import sys

base = "/home/groundhog/groundhog/data/groundhog"

for i in range(10000):
    name = base + "%04d" % i
    if (not os.path.isfile(name + ".dat")) and (not os.path.isfile(name + ".txt")):
        sys.stdout.write(name)
        break
