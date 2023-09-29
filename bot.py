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
        # Setting the NICK and REAL name of the bot
        swagBot = Bot("SwagBot", "Joseph Goldberg")
        # Defining a socket, with Ipv6 using TCP socket
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port)) # Connect using our details
            s.send(swagBot.botRegistration()) # Send NICK and USER details
            s.send(swagBot.botJoinChannel()) # Trying to join test channel
        return s

    # keepalive will keep the bot in the IRC server
    def keepalive(self, s):
        while 1:
            text = s.recv(2040)
            print(text)
        pass


    # pong will handle ping requests with a corresponding pong
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

    # botRegistration is responsible for the bot connecting to the IRC server
    # @return a formatted NICK and USER command
    def botRegistration(self):
        # Concatenating a string to create the user details
        user = "NICK " + self.nickname +  "\r\nUSER " + self.nickname + " 0 * " + ":" + self.realname +"\r\n"
        # print(user) Testing using string
        return user.encode() # We need to encode the data into bytes so it can be sent via socket.
    
    # @return
    def botJoinChannel(self):
        join = "JOIN #test\r\n" # This should be changed to allow user to pick
        return join.encode()

def main():
    # CHECK FOR USER INPUTS
    clientSocket = Socket("fc00:1337::17", 6667) # Linux IP - fc00:1337::17, Localhost = ::1, Windows IP - fc00:1337::19
    openSocket = clientSocket.connectToServer() # openSocket is the open IRC socket.
    clientSocket.keepalive(openSocket)


if __name__ == "__main__":
    main()