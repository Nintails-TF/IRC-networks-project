import socket

# Data structure to store channel membership
channels = {}
# Dictionary to store socket-nickname mapping
nicknames = {}  

# Checks for valid nickname according to IRC protocol
def is_valid_nickname(nickname):
    # Maximum length of nickname
    max_length = 15
    # Defines set of allowed characters in a nickname
    allowed_characters = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    # Valid nickname has to meet max len and allowed chars or sets false
    return len(nickname) <= max_length and all(c in allowed_characters for c in nickname)

# Uses the IPv6 addressing scheme and listens on all available interfaces
HOST = '::'
# Port num the server will listen on
PORT = 6667

# Create the socket object using IPv6 and TCP protocol
server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

try:
    # Assigns the socket to the specified host and port number
    server_socket.bind((HOST, PORT))
    
    # Enable the server to accept connections, with a backlog of 5
    server_socket.listen(5)
    print(f"Listening on {HOST} : {PORT}")

    # Waits for an incoming connection and then get the client socket and address
    client_socket, client_address = server_socket.accept()
    print(f"Accepted connection from {client_address[0]} : {client_address[1]}")

    # Store the nickname of the connected client
    nickname = None  
    # Indicate whether the USER command has been received
    user_received = False  
    
    # Used as a buffer for storing incoming messages
    buffer = ""  
    
    while True:
        # Set to read up to 4096 bytes from the client
        data = client_socket.recv(4096)

        # If no data is received, it means the client has disconnected so ends loop
        if not data:
            break

        # Adds recieved data to buffer
        buffer += data.decode('utf-8')

        # Process complete messages from the buffer
        while '\r\n' in buffer:
            message, buffer = buffer.split('\r\n', 1)
            message = message.strip()
            print(f"Received: {repr(message)}")  # Debug print of the received message
            
            # Goes through each known command and handles them
            if message.startswith('CAP LS'):
                # Respond to the CAP LS command indicating the server’s capabilities
                client_socket.send(b":server CAP * LS :\r\n")
                
            elif message.startswith('NICK'):
                # Extract and validate the nickname from the NICK command
                nickname = message.split(' ')[1]
                if not is_valid_nickname(nickname):
                    # Send an error message for invalid nicknames then skips any further processing
                    client_socket.send(b":server 432 :Erroneous Nickname\r\n")
                    continue  
                print(f"Nickname set to {nickname}")
                
            elif message.startswith('USER'):
                # Mark that the USER command has been received
                user_received = True
                print(f"USER received")
                
            elif message.startswith('CAP END') and nickname and user_received:
                # Send a welcome message after capabilities sorted
                welcome_msg = f":server 001 {nickname} :Welcome to the IRC Server!\r\n"
                print(f"Sending:\n{welcome_msg}")
                client_socket.send(welcome_msg.encode('utf-8'))
                
            else:
                # Sends error msg to client if unknown
                error_msg = f":server 421 {message.split(' ')[0]} :Unknown command\r\n"
                print(f"Sending:\n{error_msg}")
                client_socket.send(error_msg.encode('utf-8'))

except Exception as e:
    # Print any exceptions that occur
    print(f"Error: {e}")
finally:
    # Close sockets when exiting
    client_socket.close()
    server_socket.close()
