import socket
import re
import random

"""
The socket class is responsible for handling the network connections between the Bot (client) and
the server.
"""
class Socket:
    def __init__(self, host, port):
        self.host = host 
        self.port = port 

    def connectToServer(self):
        # Setting the NICK and REAL name of the bot
        swagBot = Bot("SwagBot", "Swag", [])
        # Defining a socket, with Ipv6 using TCP socket
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.send(swagBot.botRegistration()) # Send NICK and USER details
            s.send(swagBot.botJoinChannel())
            self.keepalive(s, swagBot)

    # keepalive will keep the bot in the IRC server
    def keepalive(self, s, swagBot):
        # This will loop until you CTRL+C - For testing purposes it helps to close the IRC server first then the bot.
        while True:
            try:
                # The response is the text that the bot gets from the server, we now need to parse it to perform actions.
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

    # userlist will grab the initial userlist and store it.
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
    def __init__(self, nickname, realname, userlist):
        self.nickname = nickname 
        self.realname = realname 
        self.userlist = userlist

    # addUser will add a new user to the bots userlist
    def addUser(self, text):
        print("This is the current userlist " + str(self.userlist))
        # EXTRACT THE USERNAME FROM TEXT
        username = (text.split("!")[0]).strip(":")
        self.userlist.append(username)
        print("This is the updated userlist " + str(self.userlist))
        pass

    # removeUser will remove a user from the bots userlist.
    def removeUser(self, text):
        print("This is the current userlist " + str(self.userlist))
        # EXTRACT THE USERNAME FROM TEXT
        username = (text.split("!")[0]).strip(":")
        self.userlist.remove(username)
        print("This is the updated userlist " + str(self.userlist))
        pass

    # The funnyfact function will cause the bot to respond to a private message with a fun fact
    def funnyfact(self, s, text):
        username = (text.split("!")[0]).strip(":") # Getting the username of the person who messaged us
        jokesFile = open("jokes.txt", "r")
        joke = random.choice(jokesFile.readlines()) # Randomly selecting a joke
        # Formatting a message to be sent.
        response = "PRIVMSG " + username + " :Want to hear an amazing joke? "+ joke + "\r\n"
        jokesFile.close()
        s.send(response.encode())

    # @return a formatted NICK and USER command
    def botRegistration(self):
        user = "NICK " + self.nickname +  "\r\nUSER " + self.nickname + " 0 * " + ":" + self.realname +"\r\n"
        return user.encode() 
    
    # @return a formatted join statement to join the test channel.
    def botJoinChannel(self):
        join = "JOIN #test\r\n"
        return join.encode()

def main():
    # CHECK FOR USER INPUTS
    clientSocket = Socket("fc00:1337::17", 6667) # Linux IP - fc00:1337::17, Localhost = ::1, Windows IP - fc00:1337::19
    clientSocket.connectToServer() 

if __name__ == "__main__":
    main()