import socket
import re
import random
import argparse
import time

# Initialize the default values for host, port, name, channel, and userlist
host = "::1"
port = 6667
name = "SwagBot"
channel = "#test"
userlist = []
reconnection_attempts = 0

"""
The socket class is responsible for handling the network connections between the Bot (client) and
the server.
"""
class Socket:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    # Method to connect the bot to the server with reconnection logic
    def connect_to_server(self, bot):
        while True:
            try:
                with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
                    s.connect((self.host, self.port))
                    s.send(bot.bot_registration())
                    s.send(bot.bot_join_channel())
                    self.keep_alive(s, bot)
                # Handle socket-related errors (e.g., server down, host/port issues)
            except socket.error as e:
                print(f"Socket error: {e}")
                # Implement exponential backoff with a maximum delay of 300 seconds
                delay = min(2 ** bot.reconnection_attempts, 300)
                print(f"Reconnecting in {delay} seconds...")
                time.sleep(delay)
                bot.reconnection_attempts += 1
            except KeyboardInterrupt:
                print("Bot execution interrupted.")
                break  # Exit the loop when a keyboard interrupt is detected

    # keep_alive will keep the bot in the IRC server
    def keep_alive(self, s, bot):
        # This will loop until you CTRL+C - For testing purposes it helps to close the IRC server first then the bot
        while True:
            try:
                # The response is the text that the bot gets from the server, we now need to parse it to perform actions
                response = s.recv(2048).decode()
                print(response)
                if not response:
                # Server closed the connection or an error occurred
                    print("Connection to the server has been closed.")
                    break
                if response.startswith("PING"): # If we see PING request
                    self.pong(s, response) # Respond with pong
                elif "353" in response: # When we see the 353 (userlist) IRC code.
                    response = re.findall("353(.*?)\n" , response) # Using regular expressions, we can search for text between 353 and \n to get userlist
                    self.init_user_list(response, bot) # generate a userlist
                # IF THE BOT IS PRIVATE MESSAGED (this may be with a command)
                elif "PRIVMSG" in response:
                    bot.give_fact(s, response)
                    if "!hello" in response:
                        bot.greet(s, response)
                    elif "!slap" in response:
                        bot.slap(s, response)
                    elif "!rename" in response:
                        bot.rename(s, response)
                # IF A USERS CONNECTS
                elif "JOIN" in response:
                    bot.add_user(response)
                # IF A USERS DISCONNECTs
                elif "QUIT" in response:
                    bot.remove_user(response)
            except KeyboardInterrupt:
                break
            # Handle the various errors that could occur
            except (socket.error, ConnectionResetError) as e:
                print(f"Socket error: {e}")
                break
            except MemoryError as e:
                print(f"Memory error: {e}")
                break
            except Exception as e:
                print(f"Error: {e}")
                break

    # pong will handle ping requests with a corresponding pong
    def pong(self, s, text):
        try:
            # Extract the PING message
            ping_message = text.split(" ")[1]
            # Send a PONG response back to the server
            response = "PONG " + ping_message + "\r\n"
            s.send(response.encode())
        except IndexError:
            print("Invalid PING message received, unable to send PONG response.")
        except Exception as e:
            print(f"Error handling PING request: {e}")

    def init_user_list(self, users, bot):
        try:
            if users and len(users) > 0:
                userlist = users[0].replace("\r", "")  # Remove any carriage return characters
                print(f"Raw userlist: {userlist}")
                usernames = re.findall(r':(.*?)![~@]', userlist)
                print(f"Extracted usernames: {usernames}")
                bot.userlist = usernames
        except IndexError:
            print("Error initializing userlist: Invalid input structure.")
        except Exception as e:
            print(f"Error initializing userlist: {e}")



    def get_host(self):
        return self.host

    def set_host(self, host):
        self.host = host

    def get_port(self):
        return self.port

    def set_port(self, port):
        self.port = port

"""
The Menu class is resonsible for handling user input via the CLI/terminal, ensuring that
users can input flags to modify parameters. e.g.

python bot.py --host ::1

would set the Ipv6 address to connect to the localhost.
"""
class Menu:
    def __init__(self):
        # Create an ArgumentParser object for handling command line arguments
        self.parser = argparse.ArgumentParser(description="IRC Bot Options")
        
        # Add command line arguments with default values and descriptions
        self.parser.add_argument("--host", default=host, help="IRC server host (IPv6)")
        self.parser.add_argument("--port", type=int, default=port, help="IRC server port")
        self.parser.add_argument("--name", default=name, help="Bot name (nickname and username)")
        self.parser.add_argument("--channel", default=channel, help="Channel to join")

    def get_args(self):
        # Parse the command line arguments and return the result.
        return self.parser.parse_args()

class Bot:
    def __init__(self, name, channel, userlist):
        self.name = name
        self.channel = channel
        self.userlist = userlist
        self.reconnection_attempts = reconnection_attempts

    # add_user will add a new user to the bot's userlist
    def add_user(self, text):
        print("text is -----" + text + "-----")
        print("This is the current userlist " + str(self.userlist))
        
        # Split the message by spaces and extract the username (the second part)
        parts = text.split()
        print(parts)
        if len(parts) > 1:  
            username = parts[0].lstrip(':')
            print("username is -----" + username + "-----")
            
            if "001" in parts:
                # This is a special message for the bot joining, extract the bot's username
                bot_username = parts[2]
                if bot_username not in self.userlist:
                    self.userlist.append(bot_username)
            else:
                if username not in self.userlist:
                    self.userlist.append(username)

            print("This is the updated userlist " + str(self.userlist))

    # remove_user will remove a user from the bot's userlist
    def remove_user(self, text):
        print("This is the current userlist " + str(self.userlist))
        # Split the message by spaces and extract the username (the second part)
        parts = text.split()
        if len(parts) > 1:
            username = parts[0].lstrip(':')
            print("username is -----" + username + "-----")
            self.userlist.remove(username)
        print("This is the updated userlist " + str(self.userlist))

    # Method to provide a fact from a given file
    def give_fact(self, s, text):
        username = text.split('!')[0].strip(':')
        message_parts = text.split(' ', 3)  # Split the message into parts

        if len(message_parts) >= 4:
            target = message_parts[2]  # The target recipient

            if target == self.name:
                # Use a context manager to open and read from the file
                with open("facts.txt", "r") as factsFile:
                    fact = random.choice(factsFile.readlines())
                    response = f"PRIVMSG {username} :Want to hear a cool fact? {fact}\r\n"
                s.send(response.encode())

    # A function where the bot will greet the user on command
    def greet(self, s, text):
        username = text.split('!')[0].strip(':')
        message_parts = text.split(' ')

        if len(message_parts) >= 4 and message_parts[3] == ":!hello\r\n":
            # Get the current date and time
            current_date = time.strftime("%Y-%m-%d")
            current_time = time.strftime("%H:%M:%S")

            # Form the greeting message
            greeting = f"Greetings {username}, welcome to the server! The date is {current_date}, and the time is {current_time}."

            # Send the greeting message to the channel
            response = f"PRIVMSG {self.channel} :{greeting}\r\n"
            s.send(response.encode())

    # A function where the user can choose to slap another user
    def slap(self, s, text):
        print(text)
        command_parts = text.lstrip(":").lower().split(" ")  # Convert to lowercase for case-insensitive comparison
        print(command_parts)
        sender = command_parts[0]
        print(sender)

        if len(command_parts) == 5:
            # User wants to slap a particular user
            target_user = command_parts[4].strip("\r\n").lower()  # Convert to lowercase for case-insensitive comparison
            print(target_user)
            if target_user == sender:
                # Prevent the user from slapping themselves
                response = f"PRIVMSG {self.channel} :You can't slap yourself!\r\n"
            elif target_user == self.name.lower():
                # Prevent the user from slapping the bot
                response = f"PRIVMSG {self.channel} :You can't slap the bot!\r\n"
            elif target_user not in [user.lower() for user in self.userlist]:
                # Check if the target user is not in the channel
                response = f"PRIVMSG {self.channel} :{target_user} is not in the channel! {sender} slaps themselves with a trout!\r\n"
            else:
                response = f"PRIVMSG {self.channel} :{sender} slaps {target_user} around with a large trout!\r\n"
        else:
            # User wants to slap a random user
            available_users = [user.lower() for user in self.userlist if user.lower() != self.name.lower() and user.lower() != sender]
            if not available_users:
                response = f"PRIVMSG {self.channel} :No suitable target for a slap! {sender} slaps themselves with a trout!\r\n"
            else:
                target_user = random.choice(available_users)
                response = f"PRIVMSG {self.channel} :{sender} slaps {target_user} around with a large trout!\r\n"
        s.send(response.encode())

    # A function for the user to be able to rename the bot
    def rename(self, s, text):
        command_parts = text.split(" ")  # Split the command into parts

        if len(command_parts) == 5:
            new_name = command_parts[4].strip("\r\n")

            # Update the bot's name
            self.name = new_name

            # Re-register the bot with the new name
            registration = self.bot_registration()
            s.send(registration)

            # Send a message to the channel about the renaming
            response = f"PRIVMSG {self.channel} :I have been renamed to {new_name}!\r\n"
        else:
            response = f"PRIVMSG {self.channel} :Invalid syntax. Use !rename new_name to rename the bot.\r\n"

        s.send(response.encode())

    # @return a formatted NICK and USER command
    def bot_registration(self):
        user = "NICK " + self.name +  "\r\nUSER " + self.name + " 0 * " + ":" + self.name + "\r\n"
        return user.encode() 

    # @return a formatted join statement to join the test channel
    def bot_join_channel(self):
        join = f"JOIN {self.channel}\r\n"
        return join.encode()

def main():
    menu = Menu()
    
    # Parse the command line arguments and store the result in the 'args' variable.
    args = menu.get_args()

    # Create a Socket object with the port and host specified in cli arguments
    client_socket = Socket(args.host, args.port)
    
    # Create a Bot object with the name, and channel specified in cli arguments
    bot = Bot(args.name, args.channel, [])

    # Connect the client socket to the IRC server and pass the bot object for communication
    client_socket.connect_to_server(bot)

if __name__ == "__main__":
    main()