import socket

"""
The socket class is responsible for handling the network connections between the Bot (client) and
the server.
"""
class Socket:
    def __init__(self, host, port):
        self.host = host # (localhost is default)
        self.port = port # (6667 as its default IRC port)

    # @return IRC connection
    def connectToServer(self):
        # Testing host and port details
        print(self.host , self.port)
        # Setting the NICK and REAL name of the bot
        swagBot = Bot("SwagBot", "Joseph Goldberg")
        # Defining a socket, with Ipv6 using TCP socket
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port)) # Connect using our details
            # s.send(swagBot.botNick()) # Send NICK details
            s.send(swagBot.botUser()) # Send USER details
            response = s.recv(1024) # wait for response
            print(response) # This should return RPL_WELCOME
            s.send(swagBot.botJoinChannel()) # Trying to join test channel

            # response = s.recv(1024) # wait for response
            # print(response) # This should return RPL_WELCOME
        

    # pong will ensures that ping requests are met with a pong, avoids bot being timed out.
    def pong(self):
        pass

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
    def __init__(self, nickname, realname):
        self.nickname = nickname # nickname defines the NICK details for IRC.
        self.realname = realname # userDetails defines the USER details for IRC.

    # @return formmated NICK command
    def botNick(self):
        nick = "NICK " + self.nickname
        # We need to encode the data into bytes so it can be sent
        return nick.encode()

    # botUser is responsible for creating a user command.
    # @return a formatted USER command
    def botUser(self):
        # Concatenating a string to create the user details
        user = "NICK " + self.nickname +  " USER " + self.nickname + " 0 * " + ":" + self.realname
        print(user)
        # We need to encode the data into bytes so it can be sent
        return user.encode()
    
    # @return
    def botJoinChannel(self):
        join = "JOIN #test" # This should be changed to allow user to pick
        return join.encode()

def main():
    # CHECK FOR USER INPUTS
    clientSocket = Socket("fc00:1337::17", 6667) # Linux IP - fc00:1337::17, Localhost = ::1, Windows IP - fc00:1337::19
    clientSocket.connectToServer() # SEND BOT DATA HERE

if __name__ == "__main__":
    main()