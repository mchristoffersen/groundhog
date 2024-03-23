#!/bin/bash
/home/groundhog/groundhog/process/ghog2hdf5.py /home/groundhog/groundhog/data/*.ghog
/home/groundhog/groundhog/process/makeQlook.py /home/groundhog/groundhog/data/*.h5
eog /home/groundhog/groundhog/data/*.png
