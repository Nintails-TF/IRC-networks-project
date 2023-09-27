import socket

"""
The socket class is responsible for handling the network connections between the Bot (client) and
the server.
"""
class Socket:
    def __init__(self, host, port):
        self.host = host # (localhost is default)
        self.port = port # (6667 as its default IRC port)

    # connectToServer will connect the IRC bot to the specified server.
    def connectToServer(self):
        print("XD")

    # pong will ensures that ping requests are met with a pong
    def pong(self):
        pass

"""
The Menu class is resonsible for handling user input via the CLI/terminal, ensuring that
users can input flags to modify parameters. e.g.

python bot.py --ipv6 fc00:1337::19

would set the Ipv6 address to connect to.
"""
class Menu:
    def __init__(self) -> None:
        pass

"""
The Bot class is responsible for holding all the functions that the bot must perform. e.g. getting registeration details, 
sending messages, etc.
"""
class Bot:
    def __init__(self, nickname, userDetails):
        self.nickname = nickname # nickname defines the NICK details for IRC.
        self.userDetails = userDetails # userDetails defines the USER details for IRC.

    # registerBot is responsible for registering the bots details to the IRC server.
    def registerBot(self):
        pass

def main():
    # Setting the default registration details for the bot.
    swagBot = Bot("SwagBot", "SwagBot 0 * :SwagBot ")
    clientSocket = Socket("::1", 6667)
    clientSocket.connectToServer()

if __name__ == "__main__":
    main()