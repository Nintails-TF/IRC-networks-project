import socket
import threading


class IRCServer:
    # Set the Host to IPv6 addressing scheme
    # Listen on all available interfaces
    HOST = "::"

    # Port num the server will listen on
    PORT = 6667

    def __init__(self):
        # Initialize the server socket using IPv6 and TCP protocol
        self.server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.clients = []
        self.clients_lock = threading.Lock()
        self.registered_users = []

    def bind_and_listen(self):
        # Assigns the socket to the specified host and port number
        self.server_socket.bind((self.HOST, self.PORT))

        # Enable the server to accept connections, with a backlog of 5
        self.server_socket.listen(5)
        print(f"Listening on {self.HOST} : {self.PORT}")

    def accept_connection(self):
        # Waits for an incoming connection and then get the client socket and address
        client_socket, client_address = self.server_socket.accept()
        print(f"Accepted connection from {client_address[0]} : {client_address[1]}")
        return client_socket

    def handle_individual_client(self, client_socket):
        # Create an IRCClient instance for the given socket
        client = IRCClient(client_socket, self)

        # Lock to avoid issues with many clients at once.
        self.clients_lock.acquire()

        # Appending a new client to the list
        try:
            self.clients.append(client)
        finally:
            # Unlock after appending
            self.clients_lock.release()

        # Start client tasks
        client.handle_client()

    def start(self):
        try:
            # Assigns the socket to the specified host and port number
            self.bind_and_listen()

            # Keeps the server running
            while True:
                client_socket = self.accept_connection()
                threading.Thread(
                    target=self.handle_individual_client, args=(client_socket,)
                ).start()

        # Specific handling for socket errors
        except socket.error as se:
            print(f"Socket error in client: {se}")

        # Catch all other exceptions
        except Exception as e:
            print(f"Error in client: {e}")

        finally:
            # Close socket when exitting
            self.server_socket.close()


# -------------------------------------------------------------------------------------------------------------------------------------------------------------------#


class IRCClient:
    def __init__(self, client_socket, server):
        self.client_socket = client_socket
        self.server = server
        self.nickname = None
        self.channels = []
        self.user_received = False
        self.buffer = ""
        self.is_registered = False

        # Command-handler mapping
        self.commands = {
            "CAP LS": self.handle_cap_ls,
            "NICK": self.handle_nick,
            "USER": self.handle_user,
            "CAP END": self.handle_cap_end,
            "JOIN": self.handle_join,
            "PING": self.handle_ping,
            "PRIVMSG": self.handle_private_messages,
            "QUIT": self.handle_quit,
        }

    # Sends a message to the client and logs it
    def send_message(self, message):
        print(f"Sending:\n{message}")
        self.client_socket.send(message.encode("utf-8"))

    # Checks for valid nickname according to IRC protocol
    def is_valid_nickname(self, nickname):
        # Maximum length of nickname
        max_length = 15
        # Defines set of allowed characters in a nickname
        allowed_characters = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-[]\\`^{}"
        )

        # Defines set of characters a nickname can start with
        starting_characters = set(
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        )

        # Ensure it starts with a valid character
        if nickname[0] not in starting_characters:
            return False

        # Ensure the nickname length and subsequent characters are valid
        return len(nickname) <= max_length and all(
            c in allowed_characters for c in nickname[1:]
        )

    def notify_disconnect(self):
        # If the user has a nickname and is registered.
        if self.nickname and self.nickname in self.server.registered_users:
            # Remove the nickname from list
            self.server.registered_users.remove(self.nickname)

        # Lock to safely change the client list
        with self.server.clients_lock:
            # If this client is in the list
            if self in self.server.clients:
                # Remove this client from the list
                self.server.clients.remove(self)

    def register_client(self):
        # If nickname is already taken, inform the client
        if self.nickname in self.server.registered_users:
            self.send_message(
                f":server 433 * {self.nickname} :Nickname is already in use\r\n"
            )
        else:
            self.is_registered = True
            self.server.registered_users.append(self.nickname)
            self.send_message(
                f":server 001 {self.nickname} :Welcome to the IRC Server!\r\n"
            )

    def process_message(self, message):
        # A flag to track if the command has been handled
        handled = False

        # Loop through each command/handler
        for cmd, handler in self.commands.items():
            # If the start of the message starts with a command
            if message.startswith(cmd):
                # Use the respective handler method for that command
                handler(message)
                handled = True
                break

        # If no command matches the message
        if not handled:
            # Handle the command as unknown
            self.handle_unknown(message)

    # -------------------------------------------------------------------------------------------------------------------------------------------------------------------#

    def handle_cap_ls(self, message=None):
        # Respond to the CAP LS command indicating the server’s capabilities
        self.client_socket.send(b":server CAP * LS :\r\n")

    def handle_nick(self, message):
        new_nickname = message.split(" ")[1].strip()
        old_nickname = self.nickname

        if not self.is_valid_nickname(new_nickname):
            self.send_message(":server 432 :Erroneous Nickname\r\n")
            return

        self.nickname = new_nickname

        if self.user_received and not self.is_registered:
            self.register_client()

        # Notify other clients about the nickname change, if old_nickname exists
        if old_nickname:
            notification_msg = f":{old_nickname} NICK :{new_nickname}\r\n"

            with self.server.clients_lock:  # Lock for thread safety
                for client in self.server.clients:
                    client.send_message(notification_msg)

        print(f"Nickname set to {self.nickname}")

    def handle_user(self, message=None):
        # Mark that the USER command has been received
        self.user_received = True
        if self.nickname and not self.is_registered:
            self.register_client()
        print(f"USER received")

    def handle_cap_end(self, message=None):
        # Previously was sending welcome message here but now moved to do it upon registration
        pass

    def handle_unknown(self, message):
        # Sends error msg to client if unknown command
        error_msg = f":server 421 {message.split(' ')[0]} :Unknown command\r\n"
        self.send_message(error_msg)

    def handle_join(self, message):
        # Extract the channel from the message
        channel = message.split(" ")[1]

        # If the chanel is not in the list, create a new channel
        if channel not in self.channels:
            self.channels.append(channel)
        print(f"{self.nickname} joined {channel}")

        # Sends message tto the server that X has joined channel
        self.send_message(f":{self.nickname} JOIN :{channel}\r\n")

    def handle_ping(self, message):
        ping_data = message.split(" ")[1]
        self.send_message(f"PONG :{ping_data}\r\n")

    def handle_private_messages(self, message):
        parts = message.split(" ", 2)

        if len(parts) < 3:
            return  # Invalid message format

        target_nickname = parts[1]
        message_content = parts[2]

        # Find the target client by their nickname
        target_client = None
        with self.server.clients_lock:
            for client in self.server.clients:
                if client.nickname == target_nickname:
                    target_client = client
                    break

        # If the target client is found, send the private message
        if target_client:
            private_message = (
                f":{self.nickname} PRIVMSG {target_nickname} :{message_content}\r\n"
            )
            self.send_message(private_message)
            target_client.send_message(private_message)

        else:
            # Target client not found, send an error message to the sender
            error_message = (
                f":server 401 {self.nickname} {target_nickname} :No such nickname\r\n"
            )
            self.send_message(error_message)

    def handle_quit(self, message):
        # Get the quit message if it exists
        parts = message.split(" ", 1)
        if len(parts) > 1:
            quit_msg = parts[1]
        else:
            quit_msg = f"{self.nickname} has quit"

        # Notify channels of quit
        for channel in self.channels:
            for client in self.server.clients:
                if channel in client.channels and client != self:
                    client.send_message(f":{self.nickname} QUIT :{quit_msg}\r\n")

        # Remove this client from any channels they're a part of
        self.channels = []

        # Inform the client of the QUIT
        self.send_message(f":{self.nickname} QUIT :{quit_msg}\r\n")

        # Close this client's socket
        self.client_socket.close()

        # Notify the server to remove this client from active clients
        self.notify_disconnect()

    def handle_client(self):
        try:
            while True:
                # Set to read up to 4096 bytes from the client
                data = self.client_socket.recv(4096)

                # If no data is received, it means the client has disconnected so ends loop
                if not data:
                    break

                # Adds recieved data to buffer
                self.buffer += data.decode("utf-8")

                # Process complete messages from the buffer
                while "\r\n" in self.buffer:
                    message, self.buffer = self.buffer.split("\r\n", 1)
                    message = message.strip()
                    print(f"Received: {repr(message)}")
                    self.process_message(message)

        # Specific handling for socket errors
        except socket.error as se:
            print(f"Socket error in client: {se}")

        # Catch all other exceptions
        except Exception as e:
            print(f"Error in client: {e}")
        finally:
            self.notify_disconnect()


if __name__ == "__main__":
    server = IRCServer()
    server.start()
