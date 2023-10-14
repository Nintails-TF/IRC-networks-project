from logging import shutdown
import socket
import threading
import time
import logging
logging.basicConfig(level=logging.INFO)

NICKNAME_MAX_LENGTH = 15
ALLOWED_CHARACTERS = set(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-[]\\`^{}"
)
STARTING_CHARACTERS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ")


class IRCServer:
    HOST = "::"
    PORT = 6667

    def __init__(self):
        self.s_sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.clients = []
        self.channels = {}
        self.c_lock = threading.Lock()
        self.reg_users = []
        self.disconn_times = {}

    def bind_and_listen(self):
        self.s_sock.bind((self.HOST, self.PORT))
        self.s_sock.listen(5)
        print(f"Listening on {self.HOST} : {self.PORT}")

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
        self.c_lock.acquire()
        try:
            self.clients.append(client)
        finally:
            self.c_lock.release()
        client.handle_client()

    def shutdown(self):
        self.broadcast_message(":server NOTICE :Server is shutting down\r\n")
        time.sleep(5)
        for client in self.clients:
            client.c_sock.close()
        self.s_sock.close()
        print("Server has been shut down.")

    def start(self):
        cleanup_thread = threading.Thread(target=self.cleanup_disconnects)
        cleanup_thread.daemon = True
        cleanup_thread.start()
        try:
            self.bind_and_listen()
            while True:
                c_sock = self.accept_connection()
                if c_sock:
                    threading.Thread(target=self.handle_ind_client, args=(c_sock,)).start()
                else:
                    logging.warning("Socket was none.")
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

    def get_or_create_channel(self, ch_name):
        if ch_name not in self.channels:
            self.channels[ch_name] = Channel(ch_name)
        return self.channels[ch_name]

class ClientConnection:
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

    def notify_disconnect(self):
        if self.nickname and self.nickname in self.server.reg_users:
            self.server.reg_users.remove(self.nickname)
        
        self.server.c_lock.acquire()
        try:
            if self in self.server.clients:
                self.server.clients.remove(self)
        finally:
            self.server.c_lock.release()

        # Gracefully shutting down the client socket
        try:
            if self.c_sock.fileno() != -1:  # Check whether the socket is already closed
                self.c_sock.shutdown(socket.SHUT_RDWR)
            else:
                logging.warning("Attempt to shutdown a non-socket or already closed socket.")
        except socket.error:
            logging.error(f"Socket error during shutdown: {e}")
            pass  # Ignore if the socket is already closed or in a state that doesn't allow shutdown
        self.c_sock.close()


    def handle_client(self):
        try:
            while True:
                try:
                    if self.c_sock.fileno() == -1:
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
                print(f"Client {self.nickname if self.nickname else self.c_sock.getpeername()} has disconnected.")
            else:
                print(f"Error in client: {e}")

        finally:
            self.notify_disconnect()

    def handle_timeout(self):
        try:
            ip = self.c_sock.getpeername()[0]
            self.server.disconn_times[ip] = time.time()

            for ch_name, channel in self.channels.items():
                for client in channel.clients:
                    if client != self and client.c_sock.fileno() != -1:
                        client.send_message(f":{self.nickname} QUIT :Timed out\r\n")
                channel.remove_client(self)

            self.send_message(f":server NOTICE {self.nickname} :You have been timed out due to inactivity.\r\n")

        except socket.error as e:
            logging.error(f"Socket error while handling timeout: {e}")
        except Exception as e:
            logging.error(f"Unexpected error while handling timeout: {e}")
        finally:
            self.c_sock.close()
            self.notify_disconnect()

    def process_buffered_messages(self):
        while "\r\n" in self.buffer:
            message, self.buffer = self.buffer.split("\r\n", 1)
            logging.info(f"Received: {repr(message)}")
            self.process_message(message.strip())


class ClientRegistration:
    def register_client(self):
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

    def is_valid_nickname(self, nickname):
        try:
            if not nickname:
                return False

            if nickname[0] not in STARTING_CHARACTERS:
                return False

            if len(nickname) > NICKNAME_MAX_LENGTH:
                return False
        
            if not all(c in ALLOWED_CHARACTERS for c in nickname[1:]):
                return False
            
            if ' ' in nickname or '@' in nickname:
                return False
        
            return True

        except Exception as e:
            print(f"An error occurred while validating the nickname: {e}")
            return False


class ClientMessaging:
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
            self.handle_channel_message(target, message_content)
        else:
            self.handle_user_message(target, message_content)

    def handle_channel_message(self, target, message_content):
        if target not in self.channels:
            self.send_message(
                f":server 403 {self.nickname} {target} :No such channel or not a member\r\n"
            )
            return
        
        message = f":{self.nickname} PRIVMSG {target} :{message_content}\r\n"

        for client in self.channels[target].clients:
            if client != self:
                client.send_message(message)

    def handle_user_message(self, target, message_content):
    
        if self.nickname == target:
            self.send_message(f":server 404 {self.nickname} {target} :Cannot send message to oneself\r\n")
            return

        target_client = self._find_client_by_nickname(target)
        
        if target_client:

            message = f":{self.nickname} PRIVMSG {target} :{message_content}\r\n"
            target_client.send_message(message)

        else:
            self.send_message(f":server 401 {self.nickname} {target} :No such nickname\r\n")


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
        handled = False
        for cmd, handler in self.commands.items():
            if message.upper().startswith(cmd):
                handler(message)
                handled = True
                break
        if not handled:
            self.handle_unknown(message)

    def handle_cap_ls(self, message=None):
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
        if old_nickname:
            notification_msg = f":{old_nickname} NICK :{new_nickname}\r\n"

            self.server.c_lock.acquire()
            try:
                for client in self.server.clients:
                    client.send_message(notification_msg)
            finally:
                self.server.c_lock.release()
        print(f"Nickname set to {self.nickname}")

    def handle_user(self, message=None):
        if not message:
            self.send_message(":server 461 :USER command requires a parameter\r\n")
            logging.warning("Received empty USER command")
            return

        if self.is_registered:
            self.send_message(":server 462 :You may not reregister\r\n")
            logging.warning("Attempt to reregister USER")
            return

        self.user_received = True
    
        if self.nickname and not self.is_registered:
            self.register_client()
            logging.info(f"USER command received and client registered: {self.nickname}")

        else:
            logging.info("USER command received, awaiting NICK command for registration")


    def handle_part(self, message):
        parts = message.split()
    
        if len(parts) < 2:
            self.send_message(":server 461 :Not enough parameters\r\n")
            return

        channel = parts[1].strip()

        if channel not in self.channels:
            self.send_message(f":server 403 {self.nickname} {channel} :No such channel or not a member\r\n")
            return
    
        self.channels[channel].remove_client(self)
        del self.channels[channel]
    
        part_command = f":{self.nickname} PART {channel}\r\n"
        for client in self.server.clients:
            client.send_message(part_command)



    def handle_cap_end(self, message=None):
        pass

    def handle_unknown(self, message):
        error_msg = f":server 421 {message.split(' ')[0]} :Unknown command\r\n"
        self.send_message(error_msg)

    def broadcast_to_all_clients(self, message, old_nickname):
        self.server.c_lock.acquire()
        try:
            for client in self.server.clients:
                if client.nickname != old_nickname:
                    client.send_message(message)
        finally:
            self.server.c_lock.release()

    def handle_join(self, message):
        ch_name = message.split(" ")[1].strip()
        if ch_name.startswith("#"):
            self.join_channel(ch_name)
        else:
            self.send_message(f":server 461 {ch_name} :Not enough parameters\r\n")

    def join_channel(self, ch_name):
        channel = self.server.get_or_create_channel(ch_name)

        if ch_name not in self.channels:
            channel.add_client(self)
            self.channels[ch_name] = channel
        
            join_message = f":{self.nickname} JOIN :{ch_name}\r\n"

            for client in channel.clients:
                if client != self:
                    client.send_message(join_message)
       
            users_list = " ".join(client.nickname for client in channel.clients)
            channel.send_notice("server", f"Users in {ch_name}: {users_list}")

    def handle_ping(self, message):
        ping_data = message.split(" ")[1]
        self.send_message(f"PONG :{ping_data}\r\n")

    def handle_quit(self, message):
        parts = message.split(" ", 1)
        if len(parts) > 1:
            quit_msg = parts[1]
        else:
            quit_msg = f"{self.nickname} has quit"

        for ch_name, channel in self.channels.items():
            for client in self.server.clients:
                if ch_name in client.channels and client != self:
                    client.send_message(f":{self.nickname} QUIT :{quit_msg}\r\n")

        self.channels.clear()
        self.send_message(f":{self.nickname} QUIT :{quit_msg}\r\n")
        self.notify_disconnect()
        logging.info(f"{self.nickname} has disconnnected")




    def handle_who(self, message=None):
        parts = message.split(" ")
        target_ch = parts[1] if len(parts) > 1 else None

        if target_ch is not None and not target_ch.startswith("#"):
            self.send_message(":server 403 :Invalid channel name\r\n")
            return

        clients_in_channel = []
        self.server.c_lock.acquire()
        try:
            clients_in_channel = [client for client in self.server.clients 
                                  if not target_ch or target_ch in client.channels]
        finally:
            self.server.c_lock.release()

        for client in clients_in_channel:
            if client.nickname:
                info = f":server 352 {self.nickname} {target_ch} {client.nickname} {client.c_sock.getpeername()[0]} :{client.nickname}\r\n"
                self.send_message(info)

        self.send_message(":server 315 :End of /WHO list.\r\n")

    def handle_mode(self, message):
        parts = message.split()

        if len(parts) < 2:
            self.send_message(":server 461 MODE :Not enough parameters\r\n")
            return

        target, *remaining_parts = parts[1:]
    
        if target == self.nickname:
            user_mode = remaining_parts[0] if remaining_parts else self.get_user_mode()
            message = None
       
            if remaining_parts:
                self.set_user_mode(user_mode)
                if user_mode in {"+o", "-o"}:
                    message = f":server 221 {self.nickname} :User mode set to {user_mode}\r\n"
                else:
                    message = f":server 501 {self.nickname} :Unknown MODE flag. Usage `/mode <channel/nickname> <+o/-o>`\r\n"
            else:
                message = f":server 221 {self.nickname} :User mode is {user_mode}\r\n"
        
            self.send_message(message)



    def handle_kick(self, message=None):
        self.send_message(":server 502 :KICK command is not supported\r\n")

    def handle_motd(self, message=None):
        self.send_message(":server 502 :MOTD command is not supported\r\n")

    def handle_list(self, message=None):
        print("GOT TO METHOD")
        if not self.server.channels:
            self.send_message(":server 323 :No channels available\r\n")
            return
        for ch_name, channel in self.server.channels.items():
            self.send_message(f":server 322 {self.nickname} {ch_name} :No topic set\r\n")
        self.send_message(":server 323 :End of /LIST\r\n")

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