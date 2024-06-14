import socket
import os
import ubx

# Set the path for the Unix socket
socket_path = "/tmp/gps"

# Create the Unix socket client
client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

# Connect to the server
client.connect(socket_path)

try:
    while True:
        msg = client.recv(1024)
        print(msg)
except KeyboardInterrupt:
    pass

# Shutdown
client.shutdown(socket.SHUT_RD)

# Close the connection
client.close()
