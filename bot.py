import socket
import re
import random
import argparse
from datetime import datetime

# Initialize the default values for host, port, realname, nickname, and channel
host = "::1"
port = 6667
realname = "Swag"
nickname = "SwagBot"
channel = "#test"
userlist = []

"""
The socket class is responsible for handling the network connections between the Bot (client) and
the server.
"""
class Socket:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def connectToServer(self, bot):
        # Defining a socket, with Ipv6 using TCP socket
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.send(bot.botRegistration())
            s.send(bot.botJoinChannel())
            self.keepalive(s, bot)

    # keepalive will keep the bot in the IRC server
    def keepalive(self, s, swagBot):
        # This will loop until you CTRL+C - For testing purposes it helps to close the IRC server first then the bot
        while True:
            try:
                # The response is the text that the bot gets from the server, we now need to parse it to perform actions
                response = s.recv(2048).decode()
                # print(response) # Printing out response for testing
                if response.startswith("PING"): # If we see PING request
                    self.pong(s, response) # Respond with pong
                elif "353" in response: # When we see the 353 (userlist) IRC code.
                    response = re.findall("353(.*?)\n" , response) # Using regular expressions, we can search for text between 353 and \n to get userlist
                    self.initUserlist(response, swagBot) # generate a userlist
                # IF THE BOT IS PRIVATE MESSAGED
                elif "PRIVMSG" in response:
                    swagBot.funnyfact(s, response)
                    # Check if it's a slap command
                    if "!slap" in response:
                        swagBot.slap(s, response)
                    elif "!hello" in response:
                        swagBot.greet(s, response)
                # IF A USERS CONNECTS
                elif "JOIN" in response:
                    swagBot.addUser(response)
                # IF A USERS DISCONNECTs
                elif "QUIT" in response:
                    swagBot.removeUser(response)
            except KeyboardInterrupt:
                break

    # pong will handle ping requests with a corresponding pong
    def pong(self, s, text):
        # Extract the PING message
        ping_message = text.split(" ")[1]
        # Send a PONG response back to the server
        response = "PONG " + ping_message + "\r\n"
        s.send(response.encode())

    # userlist will grab the initial userlist and store it
    def initUserlist(self, users, bot):
        userlist = users[0].replace("\r", "") # turning array into string and removing \r
        # Split the userlist at the : and " "
        userlist = userlist.split(":")
        userlist = userlist[1].split(" ")
        # print(userlist) Testing userlist
        bot.userlist = userlist

    def getHost(self):
        return self.host

    def setHost(self, host):
        self.host = host

    def getPort(self):
        return self.port

    def setPort(self, port):
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
        self.parser.add_argument("--nickname", default=nickname, help="Bot nickname")
        self.parser.add_argument("--realname", default=realname, help="Bot real name")
        self.parser.add_argument("--channel", default=channel, help="Channel to join")

    def get_args(self):
        # Parse the command line arguments and return the result.
        return self.parser.parse_args()

class Bot:
    def __init__(self, nickname, realname, userlist, channel):
        self.nickname = nickname
        self.realname = realname
        self.userlist = userlist
        self.channel = channel

    # addUser will add a new user to the bots userlist
    def addUser(self, text):
        print("This is the current userlist " + str(self.userlist))
        # EXTRACT THE USERNAME FROM TEXT
        username = (text.split("!")[0]).strip(":")
        self.userlist.append(username)
        print("This is the updated userlist " + str(self.userlist))
        pass

    # removeUser will remove a user from the bots userlist
    def removeUser(self, text):
        print("This is the current userlist " + str(self.userlist))
        # EXTRACT THE USERNAME FROM TEXT
        username = (text.split("!")[0]).strip(":")
        self.userlist.remove(username)
        print("This is the updated userlist " + str(self.userlist))
        pass

    def funnyfact(self, s, text):
        username = text.split('!')[0].strip(':')
        message_parts = text.split(' ', 3)  # Split the message into parts

        if len(message_parts) >= 4:
            target = message_parts[2]  # The target recipient

            if target == self.nickname:
                jokesFile = open("jokes.txt", "r")
                joke = random.choice(jokesFile.readlines())
                response = f"PRIVMSG {username} :Want to hear an amazing joke? {joke}\r\n"
                jokesFile.close()
                s.send(response.encode())

    def slap(self, s, text):
        command_parts = text.split(" ") # Split the command into parts
        sender = text.split("!")[0].lstrip(":").lower()  # Convert to lowercase for case-insensitive comparison

        if len(command_parts) == 5:
            # User wants to clap a particular user
            target_user = command_parts[4].strip("\r\n").lower()  # Convert to lowercase for case-insensitive comparison

            if target_user == sender:
                # Prevent the user from slapping themselves
                response = f"PRIVMSG {self.channel} :You can't slap yourself!\r\n"
            elif target_user == self.nickname.lower():
                # Prevent the user from slapping the bot
                response = f"PRIVMSG {self.channel} :You can't slap the bot!\r\n"
            else:
                response = f"PRIVMSG {self.channel} :{sender} slaps {target_user} around with a large trout!\r\n"
        else:
            # User wants to slap a random user
            available_users = [user.lower() for user in self.userlist if user.lower() != self.nickname.lower() and user.lower() != sender]
            if available_users:
                target_user = random.choice(available_users)
                response = f"PRIVMSG {self.channel} :{sender} slaps {target_user} around with a large trout!\r\n"

        s.send(response.encode())

    # Add this method to the Bot class
    def greet_user(self, s, text):
        username = text.split('!')[0].strip(':')
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Get the current date and time

        response = f"PRIVMSG {username} :Greetings {username}, welcome to the server. The date is {current_time.split()[0]}, and the time is {current_time.split()[1]}.\r\n"
        s.send(response.encode())

    # @return a formatted NICK and USER command
    def botRegistration(self):
        user = "NICK " + self.nickname +  "\r\nUSER " + self.nickname + " 0 * " + ":" + self.realname +"\r\n"
        return user.encode() 

    # @return a formatted join statement to join the test channel
    def botJoinChannel(self):
        join = "JOIN #test\r\n"
        return join.encode()

def main():
    menu = Menu()
    
    # Parse the command line arguments and store the result in the 'args' variable.
    args = menu.get_args()

    # Create a Socket object with the port and host specified in cli arguments
    clientSocket = Socket(args.host, args.port)
    
    # Create a Bot object with the nickname, real name, and channel specified in cli arguments
    bot = Bot(args.nickname, args.realname, [], args.channel)

    # Connect the client socket to the IRC server and pass the bot object for communication
    clientSocket.connectToServer(bot)


if __name__ == "__main__":
    main()
