"""
The socket class is responsible for handling the network connection between the Bot (client) and
the server
"""
class Socket:
    def __init__(self) -> None:
        pass
"""
The Menu class is resonsible for handling user input via the CLI/terminal, ensuring that
users can input flags to modify parameters. e.g.

python bot.py -ipv6 

would set the Ipv6 address to connect to.
"""
class Menu:
    def __init__(self) -> None:
        pass

"""
The Bot class is responsible for holding all the functions that the bot must perform. e.g. joining a 
IRC server, getting registered, sending messages, etc.
"""
class Bot:
    def __init__(self, nickname, userDetails):
        self.nickname = nickname # nickname defines the NICK details for IRC.
        self.userDetails = userDetails # userDetails defines the USER details for IRC.

    def main():
        # Setting the default registration details for the bot.
        swagBot = Bot("SwagBot", "SwagBot 0 * :SwagBot ")

    if __name__ == "__main__":
        main()