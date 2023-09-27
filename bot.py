class Bot:
    def __init__(self, nickname, userDetails):
        self.nickname = nickname # nickname defines the NICK details for IRC.
        self.userDetails = userDetails # userDetails defines the USER details for IRC.

    def main():
        # Setting the registration details for the bot.
        swagBot = Bot("SwagBot", "SwagBot 0 * :SwagBot ")

    if __name__ == "__main__":
        main()