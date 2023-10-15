from logging import shutdown
import socket
import threading
import time
import logging
logging.basicConfig(level=logging.INFO)

NICKNAME_MAX_LENGTH = 15
ALLOWED_CHARACTERS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-[]\\`^{}")
STARTING_CHARACTERS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


class IRCServer:
    # Default server configuration
    HOST = "::"
    PORT = 6667

     # Initialize the server with default attributes
    def __init__(self):
        self.s_sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.clients = []
        self.channels = {}
        self.c_lock = threading.Lock()
        self.reg_users = set()
        self.disconn_times = {}

    # Bind the server to the specified host and port, then start listening
    def bind_and_listen(self):
        self.s_sock.bind((self.HOST, self.PORT))
        self.s_sock.listen(5)
        print(f"Listening on {self.HOST} : {self.PORT}")

    # Retrieve an existing channel or create a new one
    def get_or_create_channel(self, ch_name):
        if ch_name not in self.channels:
            self.channels[ch_name] = Channel(ch_name)
        return self.channels[ch_name]

    # Regularly remove IPs that have passed their cooldown period
    def cleanup_disconnects(self):
        while True:
            time.sleep(30)
            curr_time = time.time()
            ips_to_remove = [
                ip
                for ip, disconn_time in self.disconn_times.items()
                if curr_time - disconn_time > 600
            ]
            for ip in ips_to_remove:
                del self.disconn_times[ip]
                print(f"Removed IP {ip} from cooldown list.")

    # Accept incoming client connections
    def accept_connection(self):
        c_sock, c_addr = self.s_sock.accept()
        print(f"Accepted connection from {c_addr[0]} : {c_addr[1]}")
        ip = c_addr[0]
        if ip in self.disconn_times and time.time() - self.disconn_times[ip] < 8:
            print(f"Connection attempt from {ip} but it's on cooldown.")
            # Inform the client of the cooldown
            c_sock.send(b"Connection denied: Your IP is on a cooldown.\n")
            c_sock.close()
            return None
        return c_sock

    # Handle an individual client's activities
    def handle_ind_client(self, c_sock):
        client = IRCClient(c_sock, self)
        self.c_lock.acquire()
        try:
            self.clients.append(client)
        finally:
            self.c_lock.release()
        client.handle_client()

    # Shut down the server and close all connections
    def shutdown(self):
        self.broadcast_message(":server NOTICE :Server is shutting down\r\n")
        time.sleep(5)
        for client in self.clients:
            client.c_sock.close()
        self.s_sock.close()
        print("Server has been shut down.")

    # Start the server and manage client connections
    def start(self):
        # Start the cleanup thread
        cleanup_thread = threading.Thread(target=self.cleanup_disconnects)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        # Main server loop
        try:
            while True:
                self.bind_and_listen()
                while True:
                    # Accept and handle new clients
                    c_sock = self.accept_connection()
                    if c_sock:
                        # Start a new thread for each client
                        threading.Thread(target=self.handle_ind_client, args=(c_sock,)).start()
                    else:
                        logging.warning("Socket was none.")
         # Handle exceptions and errors.
        except KeyboardInterrupt:
            print("\nShutting down the server gracefully...")
            self.shutdown()
        except (socket.timeout, ConnectionRefusedError) as e:
            logging.error(f"Connection error: {e}")
        except socket.error as se:
            logging.error(f"Socket error: {se}")
        except ValueError as ve:
            logging.error(f"Value error: {ve}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
        finally:
            self.s_sock.close()
            logging.info("Socket has been closed.")


class ClientConnection:
    # Send a message to the client. Handles errors and logs accordingly
    def send_message(self, message):
        if not message:
            logging.warning("Attempted to send an empty message.")
            return        

        try:
            logging.info(f"\nSending:\n{message}")
            self.c_sock.send(message.encode("utf-8"))
        except (socket.error, BrokenPipeError) as e:
            logging.error(f"An error occurred while sending the message: {e}")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")

    # Notify the server about a client's disconnection and handle cleanup
    def notify_disconnect(self):
        if self.nickname and self.nickname in self.server.reg_users:
            self.server.reg_users.remove(self.nickname)
        self.server.c_lock.acquire()
        try:
            if self in self.server.clients:
                self.server.clients.remove(self)
        finally:
            self.server.c_lock.release()
        if self.is_socket_open():
            try:
                self.c_sock.shutdown(socket.SHUT_RDWR)
            except socket.error as e:
                logging.error(f"Socket error during shutdown: {e}")
            finally:
                self.c_sock.close()
                self.disconnected = True
        else:
            logging.warning("Attempt to shutdown a non-socket or already closed socket.")
    # Main handler for the client. Processes messages and handles errors
    def handle_client(self):
        try:
            while not self.disconnected:  # Check if the client is disconnected
                try:
                    if not self.is_socket_open():
                        logging.error("Socket is already closed.")
                        return

                    self.c_sock.settimeout(IRCClient.TIMEOUT)
                except socket.error as e:
                    logging.error(f"Socket error (setting timeout): {e}")
                    return  
                except Exception as e:
                    logging.error(f"Unexpected error in client (setting timeout): {e}")
                    return           

                data = self.c_sock.recv(4096)
                if not data:
                    break
                
                try:
                    self.buffer += data.decode("utf-8")
                except UnicodeDecodeError as ue:
                    logging.error(f"Unicode decode error: {ue}")
                    continue                    

                while "\r\n" in self.buffer:
                    message, self.buffer = self.buffer.split("\r\n", 1)
                    message = message.strip()
                    logging.info(f"Received: {repr(message)}")
                    self.process_message(message)
                self.process_buffered_messages()

        except socket.timeout:
            logging.warning(
                f"Client {self.nickname if self.nickname else self.c_sock.getpeername()} timed out."
            )
        except socket.error as se:
            logging.error(f"Socket error in client: {se}")
        except ValueError as ve:
            logging.error(f"Value error: {ve}")
        except Exception as e:
            if str(e) == "Client disconnected":
                logging.info(f"Client {self.nickname if self.nickname else self.c_sock.getpeername()} has disconnected.")
            else:
                logging.error(f"Error in client: {e}")
        finally:
            if self.is_socket_open():
                self.notify_disconnect()
    # Check if the client socket is open
    def is_socket_open(self):
        try:
            return self.c_sock.fileno() != -1
        except socket.error:
            return False
    # Handle client timeouts and notify other clients
    def handle_timeout(self):
        try:
            ip = self.c_sock.getpeername()[0]
            self.server.disconn_times[ip] = time.time()
            for ch_name, channel in self.channels.items():
                for client in channel.clients:
                    if client != self and client.c_sock.fileno() != -1:
                        try:
                            client.send_message(f":{self.nickname} QUIT :Timed out\r\n")
                        except Exception as e:
                            logging.error(f"Error notifying client of timeout: {e}")

                channel.remove_client(self)
            self.send_message(f":server NOTICE {self.nickname} :You have been timed out due to inactivity.\r\n")

        except socket.error as e:
            logging.error(f"Socket error while handling timeout: {e}")
        except Exception as e:
            logging.error(f"Unexpected error while handling timeout: {e}")
        finally:
            try:
                self.c_sock.close()
            except Exception as e:
                logging.error(f"Error closing socket after timeout: {e}")
            
            self.notify_disconnect()

    # Process any buffered messages from the client.
    def process_buffered_messages(self):
        while "\r\n" in self.buffer:
            message, self.buffer = self.buffer.split("\r\n", 1)
            logging.info(f"Received: {repr(message)}")
            self.process_message(message.strip())


class ClientRegistration:
    def register_client(self):
        logging.info(f"Registering client with nickname: {self.nickname}")

        # Only register the nickname if it's not already registered
        if self.nickname not in self.server.reg_users:
            self.is_registered = True
            self.server.reg_users.add(self.nickname)  # Use add for a set
            self.send_message(
                f":server 001 {self.nickname} :Welcome to the IRC Server!\r\n"
            )
        else:
            logging.warning(f"Nickname {self.nickname} is already in the registered users set!")

    # Check if a given nickname is valid based on specific conditions (starting characters, length, allowed characters).
    def is_valid_nickname(self, nickname):
        try:
            # Check if the nickname is empty.
            if not nickname:
                return False
            # Ensure the first character is in the allowed starting characters.
            if nickname[0] not in STARTING_CHARACTERS:
                return False
            # Check if the nickname exceeds the maximum allowed length.
            if len(nickname) > NICKNAME_MAX_LENGTH:
                return False
            # Ensure all characters in the nickname are allowed.
            if not all(c in ALLOWED_CHARACTERS for c in nickname[1:]):
                return False
            # Ensure the nickname doesn't contain spaces or '@'.
            if ' ' in nickname or '@' in nickname:
                return False
        
            return True
        # Handle any exceptions that might occur during validation.
        except Exception as e:
            print(f"An error occurred while validating the nickname: {e}")
            return False


class ClientMessaging:
    # Handle private messages, determining whether they're meant for a channel or a specific user.
    def handle_private_messages(self, message):
        parts = message.split(" ", 2)
        if len(parts) < 3:
            self.send_message(":server 461 :Not enough parameters\r\n")
            return
    
        target, message_content = parts[1], parts[2].lstrip(":")
        if not message_content:
            self.send_message(":server 412 :No text to send\r\n")
            return

        if target.startswith("#"):
            self._handle_message(target, message_content, is_channel=True)
        else:
            self._handle_message(target, message_content, is_channel=False)
    # Internal method to process the actual message, based on whether it's for a channel or a user..
    def _handle_message(self, target, message_content, is_channel=True):
        """Utility function to handle user and channel messages."""
        if is_channel:
            if target not in self.channels:
                self.send_message(f":server 403 {self.nickname} {target} :No such channel or not a member\r\n")
                return
        
            message = f":{self.nickname} PRIVMSG {target} :{message_content}\r\n"
            for client in self.channels[target].clients:
                if client != self:
                    client.send_message(message)
        else:
            if self.nickname == target:
                self.send_message(f":server 404 {self.nickname} {target} :Cannot send message to oneself\r\n")
                return

            target_client = self._find_client_by_nickname(target)
            if target_client:
                message = f":{self.nickname} PRIVMSG {target} :{message_content}\r\n"
                target_client.send_message(message)
            else:
                self.send_message(f":server 401 {self.nickname} {target} :No such nickname\r\n")

    # Find a client by their nickname from the server's list of clients.
    def _find_client_by_nickname(self, nickname):
        target_client = None
        self.server.c_lock.acquire()
        try:
            for client in self.server.clients:
                if client.nickname == nickname:
                    target_client = client
                    break
        finally:
            self.server.c_lock.release()
        return target_client


class ClientCommandProcessing:
    def process_message(self, message):
        # Initialize a flag to indicate whether the message was handled by any command
        handled = False
        # Iterate over the commands and their handlers for each
        for cmd, handler in self.commands.items():
            # Check if the incoming message starts with a known command
            if message.upper().startswith(cmd):
                # Call the associated handler for the matched command
                handler(message)
                handled = True
                # Exit the loop since the command has been processed
                break
            
        # If message was not recognized as any known command, handle it as an unknown command
        if not handled:
            self.handle_unknown(message)

    # "CAP LS" command which requests a list of the server's capabilities
    def handle_cap_ls(self, message=None):
        # Sends a message indicating the server capabilities.
        self.c_sock.send(b":server CAP * LS :\r\n")

    # "NICK" command which allows clients to set or change their nickname
    def handle_nick(self, message):

        # Extract nickname from the message
        new_nickname = message.split(" ")[1].strip()
    
        # Check the desired nickname with is_valid_nickname method. If not, send an error message
        if not self.is_valid_nickname(new_nickname):
            self.send_message(":server 432 :Erroneous Nickname\r\n")
            return
    
        # Check the desired nickname is already in use. If so, send an error message
        if new_nickname in self.server.reg_users:
            self.send_message(
                f":server 433 * {new_nickname} :Nickname is already in use\r\n"
            )
            return
        
        # Store the current nickname before changing it
        old_nickname = self.nickname
        # If the old nickname exists and is in the list of registered users, remove it.
        if old_nickname and old_nickname in self.server.reg_users:
            self.server.reg_users.remove(old_nickname)
    
        # Update the client's nickname to the new one
        self.nickname = new_nickname

        # If the USER command has been received but the client is not yet registered, register the client
        if self.user_received and not self.is_registered:
            self.register_client()
            logging.info(f"USER command received and client registered: {self.nickname}")
        else:
            # If only the USER command has been received, log that the server is waiting for the NICK command to complete registration
            logging.info("USER command received, awaiting NICK command for registration")

        # If the client had an old nickname, notify all other clients about the nickname change
        if old_nickname:
            notification_msg = f":{old_nickname} NICK :{new_nickname}\r\n"
            
            # Aquire lock for safe manipulation
            self.server.c_lock.acquire()
            try:
                # Notify all clients except the one changing its nickname
                for client in self.server.clients:
                    if client != self:
                        client.send_message(notification_msg)
            finally:
                # Ensure the lock is released after notifying all clients.
                self.server.c_lock.release()

        logging.info(f"Nickname set to {self.nickname}")


    # Handles the "USER" command for client registration
    def handle_user(self, message=None):
    
        # If the message is absent, violates protocol, inform client
        if not message:
            self.send_message(":server 461 :USER command requires a parameter\r\n")
            logging.warning("Received empty USER command")
            return

        # Prevent double registration
        if self.is_registered:
            self.send_message(":server 462 :You may not reregister\r\n")
            logging.warning("Attempt to reregister USER")
            return

        # Flag that we've received the USER part of the registration process.
        self.user_received = True

        # If a nickname is set and client isn't registered, complete registration
        if self.nickname and not self.is_registered:
            self.register_client()
            # Prevent duplicate nicknames to maintain unique client identities
            if self.nickname not in self.server.reg_users:
                self.server.reg_users.append(self.nickname)
            logging.info(f"USER command received and client registered: {self.nickname}")
        else:
            logging.info("USER command received, awaiting NICK command for registration")

    # Handles the "PART" command which allows a client to leave a channel
    def handle_part(self, message):
    
        # Split the message to extract channel details
        parts = message.split()

        # If the channel details are missing, protocol violation, inform the client
        if len(parts) < 2:
            self.send_message(":server 461 :Not enough parameters\r\n")
            return

        # Extract the channel name from the message
        channel = parts[1].strip()

        # If the client is not part of the channel, inform them
        if channel not in self.channels:
            self.send_message(f":server 403 {self.nickname} {channel} :No such channel or not a member\r\n")
            return

        # Remove the client from the specified channel's list of members
        self.channels[channel].remove_client(self)
        
        # Remove the channel from the client's list of channels
        del self.channels[channel]

        # Notify all clients that this client has left the channel
        part_command = f":{self.nickname} PART {channel}\r\n"
        for client in self.server.clients:
            client.send_message(part_command)
    
    # Handles the "CAP END" command, which indicates the end of the client's capability negotiation phase.
    # Currently, this implementation does not perform any action upon receiving this command.        
    def handle_cap_end(self, message=None):
        pass

    # Handles any command that the server doesn't recognize
    def handle_unknown(self, message):
        # Constructs an error message indicating that the received command is unrecognized
        error_msg = f":server 421 {message.split(' ')[0]} :Unknown command\r\n"
        # Sends the constructed error message back to the client
        self.send_message(error_msg)

    # Broadcasts a message to all connected clients, except the one identified by the old_nickname.
    def broadcast_to_all_clients(self, message, old_nickname):
        # Acquire a lock to ensure thread-safe access to the server's list of clients.
        self.server.c_lock.acquire()
        try:
            # Loop through each connected client.
            for client in self.server.clients:
                # Exclude sending the message to the client identified by the old nickname.
                if client.nickname != old_nickname:
                    client.send_message(message)
        # Ensure that the lock is always released after processing, regardless of the outcome.
        finally:
            self.server.c_lock.release()


    # Handles the "JOIN" command, which allows a client to join a channel
    def handle_join(self, message):
        # Extract the channel name from the received message
        ch_name = message.split(" ")[1].strip()

        # Ensure the channel name starts with '#'
        if ch_name.startswith("#"):
            # Initiate the process for the client to join the specified channel
            self.join_channel(ch_name)
        else:
            # If the channel name doesn't start with '#', inform the client of the incorrect usage
            self.send_message(f":server 461 {ch_name} :Not enough parameters\r\n")


    # Allows the client to join a specified channel or creates it if it doesn't exist
    def join_channel(self, ch_name):
        # Fetch the channel object, creating it if it doesn't already exist
        channel = self.server.get_or_create_channel(ch_name)

        # If the client is not already in the specified channel:
        if ch_name not in self.channels:
            # Add the client to the channel
            channel.add_client(self)
            # Update the client's list of channels
            self.channels[ch_name] = channel

            # Construct a message indicating that the client has joined the channel.
            join_message = f":{self.nickname} JOIN :{ch_name}\r\n"

            # Notify all other clients in the channel about the new joiner
            for client in channel.clients:
                if client != self:
                    client.send_message(join_message)

            # Gather a list of all current nicknames in the channel
            user_nicknames = set(client.nickname for client in channel.clients)
            users_list = " ".join(user_nicknames)
        
            # Notify all clients in the channel about the current list of users
            notice_message = f"Users in {ch_name}: {users_list}"
            channel.send_notice("server", notice_message)

            
    # Handles the "PING" command, which checks connectivity between clients
    def handle_ping(self, message):
        
        # Extract the data associated with the PING command
        ping_data = message.split(" ")[1]
    
        # Respond to the client with a "PONG" message, echoing back the received data.
        self.send_message(f"PONG :{ping_data}\r\n")


    # Handles the "QUIT" command, allowing a client to disconnect from the server.
    def handle_quit(self, message):
        # Split the message to extract an optional quit message provided by the client.
        parts = message.split(" ", 1)
    
        if len(parts) > 1:
            quit_msg = parts[1]
        else:
            quit_msg = f"{self.nickname} has quit"

        # Notify all other clients in the channel that user quit
        for ch_name, channel in self.channels.items():
            for client in self.server.clients:
                if ch_name in client.channels and client != self:
                    client.send_message(f":{self.nickname} QUIT :{quit_msg}\r\n")

        # Clear the client's list of channels
        self.channels.clear()

        # Send a quit notification to the client itself
        self.send_message(f":{self.nickname} QUIT :{quit_msg}\r\n")

        # Mark the client as disconnected
        self.disconnected = True
    
        # Notify the server or other relevant entities about the client's disconnection
        self.notify_disconnect()
    
        # Log the disconnection event for server administration or debugging
        logging.info(f"{self.nickname} has disconnected")


    # Handles the "WHO" command, which provides information about users in a specified channel or the entire server.
    def handle_who(self, message=None):
        # Split the message to extract the channel name, if provided
        parts = message.split(" ")
        target_ch = parts[1] if len(parts) > 1 else None

        # If a channel name is provided doesn't begin with '#', it's invalid
        if target_ch is not None and not target_ch.startswith("#"):
            self.send_message(":server 403 :Invalid channel name\r\n")
            return

        # Initialize a list to store the clients in the target channel
        clients_in_channel = []
        # Acquire a lock for safety
        self.server.c_lock.acquire()
        try:
            # Populate the list with clients who are either in the specified channel or, if no channel is specified, all connected clients.
            clients_in_channel = [client for client in self.server.clients 
                                  if not target_ch or target_ch in client.channels]
        finally:
            self.server.c_lock.release()

        # Loop through each client and send the client details to the requester.
        for client in clients_in_channel:
            if client.nickname:
                info = f":server 352 {self.nickname} {target_ch} {client.nickname} {client.c_sock.getpeername()[0]} :{client.nickname}\r\n"
                self.send_message(info)

        # Indicate the end of the WHO list to the requester.
        self.send_message(":server 315 :End of /WHO list.\r\n")

    # Handles the "MODE" command, which allows clients to query or set modes for themselves or channels.
    def handle_mode(self, message):
        # Split the message to extract the target (either a channel or nickname) and the mode parameters.
        parts = message.split()

        # If the command lacks necessary parameters, inform the client
        if len(parts) < 2:
            self.send_message(":server 461 MODE :Not enough parameters\r\n")
            return

        # Separate the target from the remaining mode parameters
        target, *remaining_parts = parts[1:]

        # Check if the target of the MODE command is the client's nickname
        if target == self.nickname:
            # Determine the desired mode, or fetch the current mode if none is provided
            user_mode = remaining_parts[0] if remaining_parts else self.get_user_mode()
            message = None

            # If a mode is provided:
            if remaining_parts:
                # Set the provided mode for the client
                self.set_user_mode(user_mode)
                # Construct a confirmation message based on the provided mode
                if user_mode in {"+o", "-o"}:
                    message = f":server 221 {self.nickname} :User mode set to {user_mode}\r\n"
                else:
                    # If the mode is not recognized, inform the client about the correct usage
                    message = f":server 501 {self.nickname} :Unknown MODE flag. Usage `/mode <channel/nickname> <+o/-o>`\r\n"
            else:
                # If no mode is provided, inform the client about their current mode
                message = f":server 221 {self.nickname} :User mode is {user_mode}\r\n"
    
            # Send the constructed message to the client
            self.send_message(message)


    def handle_kick(self, message=None):
        self.send_message(":server 502 :KICK command is not supported\r\n")

    def handle_motd(self, message=None):
        self.send_message(":server 502 :MOTD command is not supported\r\n")

    # Handles the "LIST" command which provides a list of channels and their topics.
    # If there are no channels, an appropriate message is sent.
    def handle_list(self, message=None):
        print("GOT TO METHOD")
        if not self.server.channels:
            self.send_message(":server 323 :No channels available\r\n")
            return
        # For each available channel, send its name and topic (if set).
        for ch_name, channel in self.server.channels.items():
            self.send_message(f":server 322 {self.nickname} {ch_name} :No topic set\r\n")
        # Indicate the end of the channel list.
        self.send_message(":server 323 :End of /LIST\r\n")

    # Handles the "LUSERS" command which provides statistics about the server's users and channels.
    # Sends back the total number of registered users, total number of channels, and a confirmation of the server's presence.
    def handle_lusers(self, message=None):
        total_users = len(self.server.reg_users)
        total_channels = len(self.server.channels)
        self.send_message(f":server 251 {self.nickname} :There are {total_users} users on 1 server(s)\r\n")
        self.send_message(f":server 254 {self.nickname} {total_channels} :channels formed\r\n")
        self.send_message(f":server 255 {self.nickname} :I have {total_users} clients and 1 servers\r\n")


class IRCClient(
    ClientConnection, ClientRegistration, ClientMessaging, ClientCommandProcessing
):
    TIMEOUT = 500

    def __init__(self, c_sock, server):
        self.c_sock = c_sock
        self.server = server
        self.nickname = None
        self.user_mode = ""
        self.channels = {}
        self.user_received = False
        self.buffer = ""
        self.is_registered = False
        self.disconnected = False

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
            "MOTD": self.handle_motd,
            "PART": self.handle_part,
            "LIST": self.handle_list,
            "LUSERS": self.handle_lusers
        }

    def set_user_mode(self, new_mode):
        if new_mode == "+o":
            self.user_mode = "o"
        elif new_mode == "-o":
            self.user_mode = ""

    def get_user_mode(self):
        return self.user_mode


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

    def send_notice(self, sender, message):
        notice = f":{sender} NOTICE {self.name} :{message}\r\n"
        for client in self.clients:
            client.send_message(notice)


if __name__ == "__main__":
    server = IRCServer()
    server.start()
