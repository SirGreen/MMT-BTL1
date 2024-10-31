
# region Help
def welcome():
    print("Welcome to a BitTorrent program by ***, press Help to see how to use")


def display_help_overview():
    help_overview = """
    Available commands:
    + Help (Command name): View detailed explanation of a command
    + MakeTor [F] (Fo) (IPT): Create a torrent file from the input file, saves to destination folder (optional).
    + Have [FTor] (IPT): Send torrent file(s) to a tracker at the specified IP, uses default if IP not provided.
    + Down [FTor] (Fo): Download a file using the torrent, communicates with tracker at default or specified IP.
    + Preview [FTor]: View the contents of a torrent file in a human-readable format.
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
        Command: MakeTor [F] (Fo) (IPT)
        Description: Creates a torrent file from the input file path (or folder) [F]. If a folder (Fo) is provided, it saves the torrent in the specified folder. Otherwise, the default folder will be used. You can provide a folder (Fo) and an optional tracker IP (IPT). If no IP is provided, the default tracker IP will be used.
        Example: MakeTor myfile.txt /myfolder
        If no folder is specified, the torrent will be saved in the current directory.
        """,
        "have": """
        Command: Have [FTor] (IPT)
        Description: Sends the specified torrent file (or multiple files if [FTor] is a folder) to a tracker. You can provide an optional tracker IP (IPT). If no IP is provided, the default tracker IP will be used.
        Example 1: Have mytorrent.torrent 192.168.1.1
        Example 2: Have torrentFolder/ 192.168.1.1
        """,
        "down": """
        Command: Down [FTor] (Fo)
        Description: Downloads the file using the specified torrent. You can provide a folder (Fo) to store the file. If no tracker IP is provided, the default IP is used.
        Example: Down mytorrent.torrent /downloads 192.168.1.1
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