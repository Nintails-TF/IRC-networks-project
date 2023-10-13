from logging import shutdown
import socket
import threading
import time
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
        self.s_sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.clients = []
        self.channels = {}
        self.c_lock = threading.Lock()
        self.reg_users = []
        self.disconn_times = {}  # Stores recent disconnects by IP address

    def bind_and_listen(self):
        # Assigns the socket to the specified host and port number
        self.s_sock.bind((self.HOST, self.PORT))
        # Enable the server to accept connections, with a backlog of 5
        self.s_sock.listen(5)
        print(f"Listening on {self.HOST} : {self.PORT}")

    def cleanup_disconnects(self):
        while True:
            time.sleep(30)  # Clean up every 5 minutes
            curr_time = time.time()
            ips_to_remove = [ip for ip, disconn_time in self.disconn_times.items() if curr_time - disconn_time > 600]  # Remove entries older than 10 minutes
            for ip in ips_to_remove:
                del self.disconn_times[ip]

    def accept_connection(self):
        c_sock, c_addr = self.s_sock.accept()
        print(f"Accepted connection from {c_addr[0]} : {c_addr[1]}")
        ip = c_addr[0]
        if ip in self.disconn_times and time.time() - self.disconn_times[ip] < 8:
            print(f"Connection attempt from {ip} but it's on cooldown.")
            c_sock.close()
            return None
        return c_sock

    def handle_ind_client(self, c_sock):
        client = IRCClient(c_sock, self)
        # Lock to avoid issues with many clients at once.
        self.c_lock.acquire()
        try:
            # Add a client to the client list
            self.clients.append(client)
        finally:
            # Unlock after appending
            self.c_lock.release()
        # Start client tasks
        client.handle_client()

    def shutdown(self):
        # Sending a global notice to inform all users about the server shutdown
        self.broadcast_message(":server NOTICE :Server is shutting down\r\n")
        time.sleep(5)        
        # Closing all client connections
        for client in self.clients:
            client.c_sock.close()
        # Closing the server socket
        self.s_sock.close()
        print("Server has been shut down.")

    def start(self):
        try:
            # Assigns the socket to the specified host and port number
            self.bind_and_listen()
            # Keeps the server running
            while True:
                c_sock  = self.accept_connection()
                if c_sock:  # Check if c_sock is not None before starting a thread
                    threading.Thread(target=self.handle_ind_client, args=(c_sock,)).start()
                else:
                    print(f"Socket was none")
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
            self.s_sock.close()

    def get_or_create_channel(self, ch_name):
        # If channel exists, return it; otherwise, create a new one.
        if ch_name not in self.channels:
            self.channels[ch_name] = Channel(ch_name)
        return self.channels[ch_name]
    
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------#

class IRCClient:
    TIMEOUT = 100
    def __init__(self, c_sock, server):
        self.c_sock = c_sock
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
            "MODE": self.handle_mode,
            "KICK": self.handle_kick,
            "MOTD": self.handle_motd
        }

    # Sends a message to the client and logs it
    def send_message(self, message):
        try:
            print(f"Sending:\n{message}")
            self.c_sock.send(message.encode("utf-8"))
        except Exception as e:
            print(f"An error occurred while sending message: {e}")

    def notify_disconnect(self):
        # If the user has a nickname and is registered.
        if self.nickname and self.nickname in self.server.reg_users:
            # Remove the nickname from list
            self.server.reg_users.remove(self.nickname)

        # Lock to safely change the client list
        self.server.c_lock.acquire()
        try:
            # If this client is in the list
            if self in self.server.clients:
                # Remove this client from the list
                self.server.clients.remove(self)
        finally:
            self.server.c_lock.release()

    def register_client(self):
        # If nickname is already taken, inform the client
        if self.nickname in self.server.reg_users:
            self.send_message(
                f":server 433 * {self.nickname} :Nickname is already in use\r\n"
            )
        else:
            self.is_registered = True
            self.server.reg_users.append(self.nickname)
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
        self.c_sock.send(b":server CAP * LS :\r\n")

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

            self.server.c_lock.acquire()  # Lock for thread safety
            try:
                for client in self.server.clients:
                    client.send_message(notification_msg)
            finally:
                self.server.c_lock.release()

        print(f"Nickname set to {self.nickname}")
    
    # Checks for valid nickname according to IRC protocol
    def is_valid_nickname(self, nickname):
        # Ensure it starts with a valid character
        if (nickname[0] not in STARTING_CHARACTERS) or \
           (len(nickname) > NICKNAME_MAX_LENGTH) or \
           (not all(c in ALLOWED_CHARACTERS for c in nickname[1:])):
            return False
        return True

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

    def broadcast_to_all_clients(self, message, old_nickname):
        # Lock for thread safety
        self.server.c_lock.acquire()  
        try:
            for client in self.server.clients:
                # Avoid sending back to the sender
                if client.nickname != old_nickname:  
                    client.send_message(message)
        finally:
            self.server.c_lock.release()

    def handle_join(self, message):
        # Get channel name the user is attempting from the message
        ch_name = message.split(" ")[1].strip()
        if ch_name.startswith("#"):
            # Join channel if channel name starts with # so is valid
            self.join_channel(ch_name)
        else:
            # If the users input is not valid for channel joining
            self.send_message(f":server 461 {ch_name} :Not enough parameters\r\n")

    def join_channel(self, ch_name):
        # Retrieve channel or create it
        channel = self.server.get_or_create_channel(ch_name)
        
        # If channel does not exist in the users list of channels
        if ch_name not in self.channels:
            # Add user to the channel
            channel.add_client(self)
            self.channels[ch_name] = channel
        
            join_message = f":{self.nickname} JOIN :{ch_name}\r\n"
            
            # Send joining message to channel
            for client in channel.clients:
                # Avoid sending to the joining user
                if client != self:  
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
        self.server.c_lock.acquire()
        try:
            # Iterate through the clients and find the one with the matching nickname
            for client in self.server.clients:
                if client.nickname == nickname:
                    target_client = client
                    break
        finally:
            # Release the lock after the search is done
            self.server.c_lock.release()

        return target_client

    def handle_quit(self, message):
        # Get the quit message if it exists
        parts = message.split(" ", 1)
        if len(parts) > 1:
            quit_msg = parts[1]
        else:
            quit_msg = f"{self.nickname} has quit"

        # Notify channels of quit
        for ch_name, channel in self.channels.items():
            for client in self.server.clients:
                if ch_name in client.channels and client != self:
                    client.send_message(f":{self.nickname} QUIT :{quit_msg}\r\n")

        # Clear the channels dictionary
        self.channels.clear()  

        # Inform the client of the QUIT
        self.send_message(f":{self.nickname} QUIT :{quit_msg}\r\n")

        # Close this client's socket
        self.c_sock.close()

        # Notify the server to remove this client from active clients
        self.notify_disconnect()
            
    # Not yet implemented
    def handle_who(self, message=None):
        self.send_message(":server 502 :WHO command is not supported\r\n")

    # Not yet implemented
    def handle_mode(self, message):
        self.send_message(":server 502 :MODE command is not supported\r\n")
    
    # Not yet implemented
    def handle_kick(self, message=None):
        self.send_message(":server 502 :KICK command is not supported\r\n")
    
    # Not yet implemented
    def handle_motd(self, message=None):
        self.send_message(":server 502 :MOTD command is not supported\r\n")
        
 # -------------------------------------------------------------------------------------------------------------------------------------------------------------------#

    def handle_client(self):
        try:
            while True:
                # Set the timeout for the client socket.
                self.c_sock.settimeout(IRCClient.TIMEOUT)
                
                # Set to read up to 4096 bytes from the client.
                data = self.c_sock.recv(4096)
                
                # If no data is received, it means the client has disconnected so ends loop.
                if not data:
                    break

                # Adds received data to buffer.
                self.buffer += data.decode("utf-8")
                
                # Process complete messages from the buffer.
                while "\r\n" in self.buffer:
                    message, self.buffer = self.buffer.split("\r\n", 1)
                    message = message.strip()
                    print(f"Received: {repr(message)}")
                    self.process_message(message)
                self.process_buffered_messages()



        except socket.timeout:
            print(f"Client {self.nickname if self.nickname else self.c_sock.getpeername()} timed out.")
            self.notify_disconnect()  # This will remove the client from the server's list
            self.c_sock.close()
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

    def handle_timeout(self):
        # Record the disconnect time of this IP
        ip = self.c_sock.getpeername()[0]
        self.server.disconn_times[ip] = time.time()

        # Notify channels of client's timeout
        for ch_name, channel in self.channels.items():
            for client in channel.clients:  # Notice the change here, we should iterate over clients in the specific channel
                if client != self:
                    client.send_message(f":{self.nickname} QUIT :Timed out\r\n")

            # Properly remove the client from the channel's client list
            channel.remove_client(self)

        # Inform the client of the timeout
        self.send_message(f":server NOTICE {self.nickname} :You have been timed out due to inactivity.\r\n")

        # Close this client's socket
        self.c_sock.close()

        # Notify the server to remove this client from active clients
        self.notify_disconnect()

    # Process complete messages from the buffer
    def process_buffered_messages(self):
        while "\r\n" in self.buffer:
            message, self.buffer = self.buffer.split("\r\n", 1)
            print(f"Received: {repr(message)}")
            self.process_message(message.strip())
    

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
