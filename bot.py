import socket
import re
import random
import argparse
import time

host = "::1"
port = 6667
name = "SwagBot"  # Combined nickname and realname into a single 'name' attribute
channel = "#test"
userlist = []

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

    def keepalive(self, s, swagBot):
        while True:
            try:
                response = s.recv(2048).decode()
                if response.startswith("PING"):
                    self.pong(s, response)
                elif "353" in response:
                    response = re.findall("353(.*?)\n" , response)
                    self.initUserlist(response, swagBot)
                elif "PRIVMSG" in response:
                    swagBot.funnyfact(s, response)
                    if "!hello" in response:
                        swagBot.greet(s, response)
                    elif "!slap" in response:
                        swagBot.slap(s, response)
                    elif "!rename" in response:
                        swagBot.rename(s, response)
                elif "JOIN" in response:
                    swagBot.addUser(response)
                elif "QUIT" in response:
                    swagBot.removeUser(response)
            except KeyboardInterrupt:
                break

    def pong(self, s, text):
        ping_message = text.split(" ")[1]
        response = "PONG " + ping_message + "\r\n"
        s.send(response.encode())

    def initUserlist(self, users, bot):
        userlist = users[0].replace("\r", "")
        userlist = userlist.split(":")
        userlist = userlist[1].split(" ")
        bot.userlist = userlist

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
        self.parser = argparse.ArgumentParser(description="IRC Bot Options")
        self.parser.add_argument("--host", default=host, help="IRC server host (IPv6)")
        self.parser.add_argument("--port", type=int, default=port, help="IRC server port")
        self.parser.add_argument("--name", default=name, help="Bot name")  # Combined nickname and realname into a single 'name' attribute
        self.parser.add_argument("--channel", default=channel, help="Channel to join")

    def get_args(self):
        return self.parser.parse_args()

class Bot:
    def __init__(self, name, userlist, channel):
        self.name = name  # Combined nickname and realname into a single 'name' attribute
        self.userlist = userlist
        self.channel = channel

    def addUser(self, text):
        print("This is the current userlist " + str(self.userlist))
        username = (text.split("!")[0]).strip(":")
        self.userlist.append(username)
        print("This is the updated userlist " + str(self.userlist))
        pass

    def removeUser(self, text):
        print("This is the current userlist " + str(self.userlist))
        username = (text.split("!")[0]).strip(":")
        self.userlist.remove(username)
        print("This is the updated userlist " + str(self.userlist))
        pass

    def funnyfact(self, s, text):
        username = text.split('!')[0].strip(':')
        message_parts = text.split(' ', 3)

        if len(message_parts) >= 4:
            target = message_parts[2]

            if target == self.name:
                factsFile = open("facts.txt", "r")
                fact = random.choice(factsFile.readlines())
                response = f"PRIVMSG {username} :Want to hear an amazing fact? {fact}\r\n"
                factsFile.close()
                s.send(response.encode())

    def greet(self, s, text):
        username = text.split('!')[0].strip(':')
        message_parts = text.split(' ')

        if len(message_parts) >= 4 and message_parts[3] == ":!hello\r\n":
            current_date = time.strftime("%Y-%m-%d")
            current_time = time.strftime("%H:%M:%S")
            greeting = f"Greetings {username}, welcome to the server! The date is {current_date}, and the time is {current_time}."
            response = f"PRIVMSG {self.channel} :{greeting}\r\n"
            s.send(response.encode())

    def slap(self, s, text):
        command_parts = text.split(" ")
        sender = text.split("!")[0].lstrip(":").lower()

        if len(command_parts) == 5:
            target_user = command_parts[4].strip("\r\n").lower()

            if target_user == sender:
                response = f"PRIVMSG {self.channel} :You can't slap yourself!\r\n"
            elif target_user == self.name.lower():
                response = f"PRIVMSG {self.channel} :You can't slap the bot!\r\n"
            else:
                response = f"PRIVMSG {self.channel} :{sender} slaps {target_user} around with a large trout!\r\n"
        else:
            available_users = [user.lower() for user in self.userlist if user.lower() != self.name.lower() and user.lower() != sender]
            if available_users:
                target_user = random.choice(available_users)
                response = f"PRIVMSG {self.channel} :{sender} slaps {target_user} around with a large trout!\r\n"
        s.send(response.encode())

    def rename(self, s, text):
        command_parts = text.split(" ")
        print(command_parts)

        if len(command_parts) == 5:
            new_name = command_parts[4].strip("\r\n")

            # Update the bot's name
            self.name = new_name

            # Re-register the bot with the new name
            registration = self.botRegistration()
            s.send(registration)

            # Send a message to the channel about the renaming
            response = f"PRIVMSG {self.channel} :I have been renamed to {new_name}!\r\n"
            s.send(response.encode())
        else:
            response = f"PRIVMSG {self.channel} :Invalid syntax. Use !rename new_name to rename the bot.\r\n"
            s.send(response.encode())

    def botRegistration(self):
        user = "NICK " + self.name +  "\r\nUSER " + self.name + " 0 * " + ":" + self.name +"\r\n"  # Use 'name' for both nickname and realname
        return user.encode()

    def botJoinChannel(self):
        join = f"JOIN {self.channel}\r\n"
        return join.encode()

def main():
    menu = Menu()
    args = menu.get_args()
    clientSocket = Socket(args.host, args.port)
    bot = Bot(args.name, [], args.channel)
    clientSocket.connectToServer(bot)

if __name__ == "__main__":
    main()
