import socket

#Define server constants
HOST = '::'  # listen on all IPv6 addresses
PORT = 6667

#Create the socket
s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

#Bind the socket to the host and the port
s.bind((HOST, PORT))

#Listen for incoming connections 
s.listen(5)
print(f"Listening on {HOST} : {PORT}")


clients_info = {}

while True:
    #Accept incoming connections
    client_socket, client_address = s.accept()
    print(f"Accepted connection from {client_address[0]} : {client_address[1]}")
    
    #Remember client's info
    clients_info[client_socket] = {"address": client_address}
