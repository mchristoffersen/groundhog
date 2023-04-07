echo "This will show you 4-5 GPGGA strings if the GPS is working (wait 5 seconds):"
gpspipe -d -r -t -o /home/radar/groundhog/control/gps_test.txt
sleep 5
pkill gpspipe
grep GPGGA /home/radar/groundhog/control/gps_test.txt
echo "Done"
