import socket

def is_valid_nickname(nickname):
    # Max length of username
    max_length = 15
    # All characters in this string are allowed for names
    allowed_characters = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    return len(nickname) <= max_length and all(c in allowed_characters for c in nickname)

# Defines server constaints
HOST = '::'
PORT = 6667

# Create the socket object for IPv6 TCP connection
server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

try:
    # Bind the socket to the specified host and port
    server_socket.bind((HOST, PORT))
    
    # Listen for incoming connections with a backlog queue of 5
    server_socket.listen(5)
    print(f"Listening on {HOST} : {PORT}")

    # Accept incoming connections
    client_socket, client_address = server_socket.accept()
    print(f"Accepted connection from {client_address[0]} : {client_address[1]}")

    # Variable to store the nickname of the connected client
    nickname = None  
    # Variable to indicate whether the USER command is received
    user_received = False  

    # Initialize a buffer to store incoming data
    buffer = ""  

    while True:
        # Receive data from the client
        data = client_socket.recv(4096)

        # If no data is received, the client has disconnected
        if not data:
            break

        # Append incoming data to the buffer
        buffer += data.decode('utf-8')

        # Process each message in the buffer
        while '\r\n' in buffer:
            # Extract the first message from the buffer and strip leading and trailing whitespaces
            message, buffer = buffer.split('\r\n', 1)
            message = message.strip()
            # Using repr to visualize non-printable characters and any extra spaces.
            print(f"Received: {repr(message)}")  

            # Respond CAP LS command with the server's capabilities
            if message.startswith('CAP LS'):
                client_socket.send(b":server CAP * LS :\r\n")
            # Extract and store the client's nickname when the NICK command is received
            elif message.startswith('NICK'):
                nickname = message.split(' ')[1]
                if not is_valid_nickname(nickname):
                    client_socket.send(b":server 432 :Erroneous Nickname\r\n")
                    # Go to the next iteration of the while loop.
                    continue  
                print(f"Nickname set to {nickname}")
            
            # Set the user_received flag to True when the USER command is received
            elif message.startswith('USER'):
                user_received = True
                print(f"USER received")
            
            # Send the welcome message when CAP END is received, and both NICK and USER have been processed
            elif message.startswith('CAP END') and nickname and user_received:
                welcome_msg = f":server 001 {nickname} :Welcome to the IRC Server!\r\n"
                print(f"Sending:\n{welcome_msg}")
                client_socket.send(welcome_msg.encode('utf-8'))
            else:
                client_socket.send(b":server 421 :Unknown command\r\n")
except Exception as e:
    print(f"Error: {e}")
finally:
    # Close the client and server sockets
    client_socket.close()
    server_socket.close()
