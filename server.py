import socket
import threading
NICKNAME_MAX_LENGTH = 15
ALLOWED_CHARACTERS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-[]\\`^{}")
STARTING_CHARACTERS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


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
        self.channels = {}
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
            
        # Catch value errror
        except ValueError as ve:
            print(f"Value error: {ve}")

        # Catch all other exceptions
        except Exception as e:
            print(f"Error in client: {e}")

        finally:
            # Close socket when exitting
            self.server_socket.close()

    def get_or_create_channel(self, channel_name):
        # If channel exists, return it; otherwise, create a new one.
        if channel_name not in self.channels:
            self.channels[channel_name] = Channel(channel_name)
        return self.channels[channel_name]


# -------------------------------------------------------------------------------------------------------------------------------------------------------------------#


class IRCClient:
    def __init__(self, client_socket, server):
        self.client_socket = client_socket
        self.server = server
        self.nickname = None
        self.channels = {}
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
            "WHO": self.handle_who,
        }

    # Sends a message to the client and logs it
    def send_message(self, message):
        try:
            print(f"Sending:\n{message}")
            self.client_socket.send(message.encode("utf-8"))
        except Exception as e:
            print(f"An error occurred while sending message: {e}")

    # Checks for valid nickname according to IRC protocol
    def is_valid_nickname(self, nickname):

        # Ensure it starts with a valid character
        if (nickname[0] not in STARTING_CHARACTERS) or \
           (len(nickname) > NICKNAME_MAX_LENGTH) or \
           (not all(c in ALLOWED_CHARACTERS for c in nickname[1:])):
            return False
        return True

    def notify_disconnect(self):
        # If the user has a nickname and is registered.
        if self.nickname and self.nickname in self.server.registered_users:
            # Remove the nickname from list
            self.server.registered_users.remove(self.nickname)

        # Lock to safely change the client list
        self.server.clients_lock.acquire()
        try:
            # If this client is in the list
            if self in self.server.clients:
                # Remove this client from the list
                self.server.clients.remove(self)
        finally:
            self.server.clients_lock.release()

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

            self.server.clients_lock.acquire()  # Lock for thread safety
            try:
                for client in self.server.clients:
                    client.send_message(notification_msg)
            finally:
                self.server.clients_lock.release()

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
        channel_name = message.split(" ")[1].strip()
        if not channel_name.startswith("#"):
            self.send_message(f":server 461 {channel_name} :Not enough parameters\r\n")
            return
        channel = self.server.get_or_create_channel(channel_name)

        # Check if already in the channel
        if channel_name not in self.channels:
            # Add client to channel
            channel.add_client(self)
            # Update client's list of channels
            self.channels[channel_name] = channel
            
        # Broadcast the join message to all clients in the channel
        join_message = f":{self.nickname} JOIN :{channel_name}\r\n"
        for client in channel.clients:
            if client != self:  # We do not want to send the join message to the joining user itself.
                client.send_message(join_message)

    def handle_ping(self, message):
        ping_data = message.split(" ")[1]
        self.send_message(f"PONG :{ping_data}\r\n")

    def handle_private_messages(self, message):
        # Split the message into three parts: command, target, and content
        parts = message.split(" ", 2)

        # Validation of if the message is in and invalid format or not
        if len(parts) < 3:
            return

        # Colon was appearing at the start of message content so removing if there
        # Extract the target of the message and message content from the split parts
        target, message_content = parts[1], parts[2].lstrip(":")

        # Channel message handling (Whole channel)
        if target.startswith("#"):
            self._handle_channel_message(target, message_content)
        # Private message handling (user to user)
        else:
            self._handle_user_message(target, message_content)

    def _handle_channel_message(self, target, message_content):
        # If the target channel isn't recognized or the user isn't a member, send an error
        if target not in self.channels:
            self.send_message(
                f":server 403 {self.nickname} {target} :No such channel or not a member\r\n"
            )
            return

        # Construct the message to be sent to the channel
        message = f":{self.nickname} PRIVMSG {target} :{message_content}\r\n"

        # Iterate through clients in the target channel and send the message to each one
        for client in self.channels[target].clients:
            # Except for the sender of message
            if client != self:
                client.send_message(message)

    def _handle_user_message(self, target, message_content):
        # Search for the target client by their nickname
        target_client = self._find_client_by_nickname(target)

        # If the target client was found, send them the message
        if target_client:
            message = f":{self.nickname} PRIVMSG {target} :{message_content}\r\n"
            target_client.send_message(message)
        else:
            # If not found, inform the sender with an error message
            self.send_message(
                f":server 401 {self.nickname} {target} :No such nickname\r\n"
            )

    def _find_client_by_nickname(self, nickname):
        target_client = None

        # Acquire the lock to ensure thread safety while searching for clients by nickname
        self.server.clients_lock.acquire()
        try:
            # Iterate through the clients and find the one with the matching nickname
            for client in self.server.clients:
                if client.nickname == nickname:
                    target_client = client
                    break
        finally:
            # Release the lock after the search is done
            self.server.clients_lock.release()

        return target_client

    def handle_quit(self, message):
        # Get the quit message if it exists
        parts = message.split(" ", 1)
        if len(parts) > 1:
            quit_msg = parts[1]
        else:
            quit_msg = f"{self.nickname} has quit"

        # Notify channels of quit
        for channel_name, channel in self.channels.items():
            for client in self.server.clients:
                if channel_name in client.channels and client != self:
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
        
        # Catch value errror
        except ValueError as ve:
            print(f"Value error: {ve}")
        
        # Catch all other exceptions
        except Exception as e:
            print(f"Error in client: {e}")
        finally:
            self.notify_disconnect()

    def handle_who(self, message):
        # If the message is not in correct format
        if len(message.split(" ")) < 2:
            self.send_message(
                f":server 461 {self.nickname} WHO :Not enough parameters\r\n"
            )
            return

        # Get the channel name
        channel_name = message.split(" ")[1].strip()

        # If the channel doesn't exist
        if channel_name not in self.channels:
            self.send_message(
                f":server 403 {self.nickname} {channel_name} :No such channel\r\n"
            )
            return

        # Get the channel object
        channel = self.channels[channel_name]

        # Get the list of clients in the channel
        clients = channel.clients

        # Send the list of clients to the user
        for client in clients:
            self.send_message(
                f":server 352 {self.nickname} {channel_name} {client.nickname} {client.nickname} {client.client_socket.getpeername()[0]} {self.nickname} H :0 {client.nickname}\r\n"
            )

        # Send the end of WHO list message
        self.send_message(
            f":server 315 {self.nickname} {channel_name} :End of WHO list\r\n"
        )


class Channel:
    def __init__(self, name):
        self.name = name
        self.clients = []

    def add_client(self, client):
        if client not in self.clients:
            self.clients.append(client)
            client.send_message(f":{client.nickname} JOIN :{self.name}\r\n")

    def remove_client(self, client):
        if client in self.clients:
            self.clients.remove(client)
            client.send_message(f":{client.nickname} PART :{self.name}\r\n")

    def broadcast(self, message, origin_client):
        for client in self.clients:
            if client != origin_client:
                client.send_message(
                    f":{origin_client.nickname} PRIVMSG {self.name} :{message}\r\n"
                )


if __name__ == "__main__":
    server = IRCServer()
    server.start()
