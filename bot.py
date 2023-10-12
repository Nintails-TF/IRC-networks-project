import socket
import argparse
import re

# Initialize the default values for host, port, realname, nickname, and channel
host = "::1"
port = 6667
realname = "Swag"
nickname = "SwagBot"
channel = "#test"

"""
The socket class is responsible for handling the network connections between the Bot (client) and
the server.
"""
class Socket:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def connectToServer(self, bot):
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.send(bot.botRegistration())
            s.send(bot.botJoinChannel())
            self.keepalive(s, bot)

    # keepalive will keep the bot in the IRC server
    def keepalive(self, s, bot):
        # This will loop until you CTRL+C
        while True:
            try:
                # The response is the text that the bot gets from the server, we now need to parse it to perform actions.
                response = s.recv(2048).decode()
                # print(response) # Printing out response for testing
                if response.startswith("PING"): # If we see PING request
                    self.pong(s, response) # Respond with pong
                elif "353" in response: # When we see the 353 (userlist) IRC code.
                    response = re.findall("353(.*?)\n" , response) # Using regular expressions, we can search for text between 353 and \n to get userlist
                    bot.initUserlist(response) # generate a userlist
                # IF THE BOT IS PRIVATE MESSAGED
                elif "PRIVMSG" in response:
                    bot.funnyfact(s, response)
                # IF USERS CONNECT/DISCONNECT
            except KeyboardInterrupt:
                break

    def pong(self, s, text):
        ping_message = text.split(" ")[1]
        response = "PONG " + ping_message + "\r\n"
        s.send(response.encode())

    def getHost(self):
        return self.host

    def setHost(self, host):
        self.host = host

    def getPort(self):
        return self.port

    def setPort(self, port):
        self.port = port

"""
The Menu class is responsible for handling user input via the CLI/terminal, ensuring that
users can input flags to modify parameters. e.g.

python bot.py --host fc00:1337::19

would set the IPv6 address to connect to.
"""
class Menu:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="IRC Bot Configuration")
        self.parser.add_argument('--host', default=host, help="IPv6 address to connect to")
        self.parser.add_argument('--port', type=int, default=port, help="Port to connect to")
        self.parser.add_argument('--nickname', default=nickname, help="Nickname of the bot")
        self.parser.add_argument('--realname', default=realname, help="Real name of the bot")
        self.parser.add_argument('--channel', default=channel, help="Channel to join")

    def parse_arguments(self):
        return self.parser.parse_args()

"""
The Bot class is responsible for holding all the functions that the bot must perform. e.g. getting registration details, 
sending messages, etc.
"""
class Bot:
    def __init__(self, nickname, realname, channel):
        self.nickname = nickname
        self.realname = realname
        self.channel = channel
        self.userlist = []

    # @return a formatted NICK and USER command
    def botRegistration(self):
        user = "NICK " + self.nickname + "\r\nUSER " + self.nickname + " 0 * " + ":" + self.realname + "\r\n"
        return user.encode()

    # @return a formatted join statement to join the test channel.
    def botJoinChannel(self):
        join = "JOIN " + self.channel + "\r\n"
        return join.encode()

    # handlePrivateMessage will respond to a private message with a fun fact
    def handlePrivateMessage(self, s, text):
        print(text)
        # We need to get the user who sent us a private message then to respond to them.
        username = text.split("!")[0]  # Getting the username of the person who messaged us
        print(username)
        self.funnyfact(s, username)

    # Respond to a private message with a fun fact
    def funnyfact(self, s, recipient):
        response = f"PRIVMSG {recipient} :Here's a fun fact for you: This bot is awesome!\r\n"
        s.send(response.encode())

    # initUserlist will grab the initial userlist and store it.
    def initUserlist(self, users):
        userlist = users[0].replace("\r", "") # turning array into string and removing \r
        # Split the userlist at the : and " "
        userlist = userlist.split(":")
        userlist = userlist[1].split(" ")
        self.userlist = userlist

def main():
    menu = Menu()
    args = menu.parse_arguments()
    clientSocket = Socket(args.host, args.port)
    swagBot = Bot(args.nickname, args.realname, args.channel)
    clientSocket.connectToServer(swagBot)

if __name__ == "__main__":
    main()
