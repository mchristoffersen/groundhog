#!/bin/bash

# Options:
# stack - how many pulses to stack into each recorded trace
# trigger - trigger threshold, comparison is absolute value so a threshold
#           of X triggers on +/-X
# spt - samples per trace (default 25 MHz)
# pretrig - number of pre-trigger samples to save in each trace

filename=$(/home/groundhog/groundhog/control/generate-filename.py)

gpspipe -d -r -u -o "$filename.txt"
./src/radar --file "$filename.ghog" --trigger 10000 --pretrig 8 --spt 512 --stack 256
pkill gpspipe
