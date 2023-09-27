import socket

# define server constants
HOST = '::'  # listen on all IPv6 addresses
PORT = 6667

# create the socket
s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

# bind the socket to the host and the port
s.bind((HOST, PORT))

# listen for incoming connections 
s.listen(5)
print(f"Listening on {HOST} : {PORT}")

while True:
    # accept incoming connections
    client_socket, client_address = s.accept()
    print(f"Accepted connection from {client_address[0]} : {client_address[1]}")