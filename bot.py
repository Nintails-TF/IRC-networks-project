import socket
import argparse
import re

# Initialize the default values for host, port, realname, nickname, and channel
host = "::1"
port = 6667
realname = "Swag"
nickname = "SwagBot"
channel = "#test"

class Bot:
    def __init__(self, nickname, realname, channel):
        self.nickname = nickname
        self.realname = realname
        self.channel = channel
        self.userlist = []

    def botRegistration(self):
        user = "NICK " + self.nickname + "\r\nUSER " + self.nickname + " 0 * " + ":" + self.realname + "\r\n"
        return user.encode()

    def botJoinChannel(self):
        join = "JOIN " + self.channel + "\r\n"
        return join.encode()

    def initUserlist(self, users):
        userlist = users.split("353")
        print(userlist)

# Updated funnyfact function
    def funnyfact(self, s, text):
        print(text)
        # Extract the username from the PRIVMSG command
        parts = text.split("!")
        if len(parts) > 0:
            username = parts[0][1:]  # Remove the leading ":" from the username
            print(username)
            response = f"PRIVMSG {username} :Here's a fun fact!\r\n"
            s.send(response.encode())

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

def main():
    menu = Menu()
    args = menu.parse_arguments()
    clientSocket = Socket(args.host, args.port)
    swagBot = Bot(args.nickname, args.realname, args.channel)
    clientSocket.connectToServer(swagBot)

if __name__ == "__main__":
    main()
