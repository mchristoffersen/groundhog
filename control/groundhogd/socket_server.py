import socket
import os
import select

# socat command
# socat /dev/ttyACM0,b115200,raw,echo=0 UNIX-CONNECT:/tmp/gps

# Set the path for the Unix socket
socket_path = socket_path = "/tmp/gps"

# remove the socket file if it already exists
try:
    os.unlink(socket_path)
except OSError:
    if os.path.exists(socket_path):
        raise RuntimeError("Failed to delete socket path")

# Create the Unix socket server
server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

# Bind the socket to the path
server.bind(socket_path)

# Listen for one connection
server.listen(1)

try:
    while True:
        while True:
            # Wait for client connection
            ready = select.select([server], [], [], 1)[0]
            if len(ready) > 0:
                connection, _ = server.accept()
                break
        while True:
            msg = connection.recv(65536)
            if(msg == b""):
                connection.close()
                break
            print(msg)
except KeyboardInterrupt:
    pass