echo "This will show you NMEA strings if the GPS is working (wait 5 seconds):"
gpspipe -d -r -u -o /home/groundhog/groundhog/control/gps_test.txt
sleep 5
pkill gpspipe
#grep GPGGA /home/groundhog/groundhog/control/gps_test.txt
cat /home/groundhog/groundhog/control/gps_test.txt
rm /home/groundhog/groundhog/control/gps_test.txt
echo "Done"
