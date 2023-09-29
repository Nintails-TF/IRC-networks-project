import socket

class IRCServer:
    def __init__(self):
        # Set the Host to IPv6 addressing scheme
        # Listen on all available interfaces
        self.HOST = '::'
        
        # Port num the server will listen on
        self.PORT = 6667

        # Initialize the server socket using IPv6 and TCP protocol
        self.server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

    def start(self):
        try:
            # Assigns the socket to the specified host and port number
            self.server_socket.bind((self.HOST, self.PORT))
            
            # Enable the server to accept connections, with a backlog of 5
            self.server_socket.listen(5)
            print(f"Listening on {self.HOST} : {self.PORT}")

            # Waits for an incoming connection and then get the client socket and address
            client_socket, client_address = self.server_socket.accept()
            print(f"Accepted connection from {client_address[0]} : {client_address[1]}")
            
            
            client = IRCClient(client_socket)
            client.handle_client()
            
        # Catch any exceptions and print error
        except Exception as e:
            print(f"Error: {e}")
        finally:
            # Close socket when exitting
            self.server_socket.close()


class IRCClient:
    def __init__(self, client_socket):
        self.client_socket = client_socket
        self.nickname = None
        self.user_received = False
        self.buffer = ""
        
    # Checks for valid nickname according to IRC protocol
    def is_valid_nickname(self, nickname):
        # Maximum length of nickname
        max_length = 15
        # Defines set of allowed characters in a nickname
        allowed_characters = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
        # Valid nickname has to meet max len and allowed chars or sets false
        return len(nickname) <= max_length and all(c in allowed_characters for c in nickname)

    def handle_client(self):
        try:
            while True:
                # Set to read up to 4096 bytes from the client
                data = self.client_socket.recv(4096)
                
                # If no data is received, it means the client has disconnected so ends loop
                if not data:
                    break

                # Adds recieved data to buffer
                self.buffer += data.decode('utf-8')

                # Process complete messages from the buffer
                while '\r\n' in self.buffer:
                    message, self.buffer = self.buffer.split('\r\n', 1)
                    message = message.strip()
                    print(f"Received: {repr(message)}")

                     # Goes through each known command and handles them
                    if message.startswith('CAP LS'):
                        # Respond to the CAP LS command indicating the server’s capabilities
                        self.client_socket.send(b":server CAP * LS :\r\n")

                    elif message.startswith('NICK'):
                        # Extract and validate the nickname from the NICK command
                        self.nickname = message.split(' ')[1]
                        if not self.is_valid_nickname(self.nickname):
                            # Send an error message for invalid nicknames then skips any further processing
                            self.client_socket.send(b":server 432 :Erroneous Nickname\r\n")
                            continue
                        print(f"Nickname set to {self.nickname}")

                    elif message.startswith('USER'):
                        # Mark that the USER command has been received
                        self.user_received = True
                        print(f"USER received")

                    elif message.startswith('CAP END') and self.nickname and self.user_received:
                        # Send a welcome message after capabilities sorted
                        welcome_msg = f":server 001 {self.nickname} :Welcome to the IRC Server!\r\n"
                        print(f"Sending:\n{welcome_msg}")
                        self.client_socket.send(welcome_msg.encode('utf-8'))

                    else:
                        # Sends error msg to client if unknown command
                        error_msg = f":server 421 {message.split(' ')[0]} :Unknown command\r\n"
                        print(f"Sending:\n{error_msg}")
                        self.client_socket.send(error_msg.encode('utf-8'))

        except Exception as e:
            # Print any exceptions that occur
            print(f"Error: {e}")
        finally:
            # Close socket when exitting
            self.client_socket.close()

if __name__ == "__main__":
    server = IRCServer()
    server.start()
