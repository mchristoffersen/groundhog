#!/bin/bash

# Options:
# stack - how many pulses to stack into each recorded trace
# trigger - trigger threshold, comparison is absolute value so a threshold
#           of X triggers on +/-X
# spt - samples per trace (the radar has a fixed sampling rate of 20 MHz)
# pretrig - number of pre-trigger samples to save in each trace

filename=$(/home/radar/groundhog/control/generate-filename.py)

gpspipe -d -r -t -o "$filename.txt"
./src/radar --file "$filename.dat" --pretrig 8 --spt 512 --stack 500 --trigger 2500
pkill gpspipe
