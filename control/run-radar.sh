#!/bin/bash

filename=$(/home/radar/groundhog/control/generate-filename.py)

gpspipe -d -r -t -o "$filename.txt"
./src/radar --file "$filename.dat" --stack 1000 --trigger 2500
pkill gpspipe
