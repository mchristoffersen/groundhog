echo "This will show you NMEA strings if the GPS is working (wait 5 seconds):"
gpspipe -d -r -u -o /home/radar/groundhog/control/gps_test.txt
sleep 5
pkill gpspipe
#grep GPGGA /home/radar/groundhog/control/gps_test.txt
cat /home/radar/groundhog/control/gps_test.txt
rm /home/radar/groundhog/control/gps_test.txt
echo "Done"
