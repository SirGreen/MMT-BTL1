
# region Help
def welcome():
    print("Welcome to a BitTorrent program by ***, press Help to see how to use")


def display_help_overview():
    help_overview = """
    Available commands:
    + Help (Command name): View detailed explanation of a command
    + MakeTor [F] (IPT): Create a torrent file from the input file for the specified IP, uses default if IP not provided.
    + Have [FTor]: Send torrent file(s) to a tracker of the torrent file.
    + Down [FTor]: Download a file using the torrent, communicates with tracker of the torrent file.
    + Preview [FTor]: View the contents of a torrent file in a human-readable format.
    + Progress
    + Status
    + Exit: Exit the program
    """
    print(help_overview)


def display_command_help(command):
    detailed_help = {
        "help": """
        Command: Help (Command name)
        Description: Use 'Help' followed by the command name to get detailed usage instructions for that specific command.
        Example: Help MakeTor
        """,
        "maketor": """
        Command: MakeTor [F] (IPT)
        Description: Creates a torrent file from the input file path (or folder) [F]. If no IP of tracker (IPT) is provided, the default tracker IP will be used.
        Example: MakeTor myfile.txt 192.168.1.1
        """,
        "have": """
        Command: Have [FTor]
        Description: Sends the specified torrent file (or multiple files if [FTor] is a folder) to a tracker.
        Example 1: Have mytorrent.torrent 192.168.1.1
        Example 2: Have torrentFolder/ 192.168.1.1
        """,
        "down": """
        Command: Down [FTor]
        Description: Downloads the file using the specified torrent to folder /downloads. 
        Example: Down mytorrent.torrent
        """,
        "preview": """
        Command: Preview [FTor]
        Description: Displays the contents of the given torrent file in a readable format. Useful for checking torrent details before downloading.
        Example: Preview mytorrent.torrent
        """,
        "Exit": """
        Description: Exit the program
        """,
    }

    if command in detailed_help:
        print(detailed_help[command])
    else:
        print("Command not found. Use 'Help' for a list of commands.")


# endregion