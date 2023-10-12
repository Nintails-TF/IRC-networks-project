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

    def keepalive(self, s, bot):
        while True:
            try:
                response = s.recv(2048).decode()
                print(response)
                if response.startswith("PING"):
                    self.pong(s, response)
                elif "353" in response:
                    self.userlist(s, response, bot)
                elif "PRIVMSG" in response:
                    bot.funnyfact(s, response)
            except KeyboardInterrupt:
                break

    def pong(self, s, text):
        ping_message = text.split(" ")[1]
        response = "PONG " + ping_message + "\r\n"
        s.send(response.encode())

    def userlist(self, s, text, bot):
        print(text.split("353"))
        bot.initUserlist(text)

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

    def funnyfact(self, s, text):
        sender = text.split('!')[0][1:]
        message_content = text.split('PRIVMSG')[1].strip()
        
        # Extract the recipient's username from the message content
        recipient = message_content.split(" ")[0]
        
        # Respond to the private message
        response = f'PRIVMSG {recipient} :Hello, {sender}! This is a response to your private message: {message_content}\r\n'
        s.send(response.encode())

    # initUserlist will grab the initial userlist and store it.
    def initUserlist(self, users):
        userlist = users.split("353")
        print(userlist)

def main():
    menu = Menu()
    args = menu.parse_arguments()
    clientSocket = Socket(args.host, args.port)
    swagBot = Bot(args.nickname, args.realname, args.channel)
    clientSocket.connectToServer(swagBot)

if __name__ == "__main__":
    main()
