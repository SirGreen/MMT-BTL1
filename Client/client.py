# Bittorrent Program Simulation
import os
import hashlib
import bencodepy  # For Bencoding (install using pip install bencodepy)

BLOCK_SZ = 512
DEFAULT_TRACKER = "http://hello.com"

# Function to show welcome message


def welcome():
    print("Welcome to a BitTorrent program by ***, press Help to see how to use")


# Function to display help overview


def display_help_overview():
    help_overview = """
    Available commands:
    + Help (Command name): View detailed explanation of a command
    + MakeTor [F] (Fo) (IPT): Create a torrent file from the input file, saves to destination folder (optional).
    + Have [FTor] (Fo) (IPT): Send the torrent file to a tracker at the specified IP, uses default if IP not provided.
    + Down [FTor] (Fo): Download a file using the torrent, communicates with tracker at default or specified IP.
    + Preview [FTor]: View the contents of a torrent file in a human-readable format.
    + Exit: Exit the program
    """
    print(help_overview)


# Function to display detailed explanation of a specific command


def display_command_help(command):
    detailed_help = {
        "Help": """
        Command: Help (Command name)
        Description: Use 'Help' followed by the command name to get detailed usage instructions for that specific command.
        Example: Help MakeTor
        """,
        "MakeTor": """
        Command: MakeTor [F] (Fo) (IPT)
        Description: Creates a torrent file from the input file path [F]. If a folder (Fo) is provided, it saves the torrent in the specified folder. Otherwise, the default folder will be used. You can provide a folder (Fo) and an optional tracker IP (IPT). If no IP is provided, the default tracker IP will be used.
        Example: MakeTor myfile.txt /myfolder
        If no folder is specified, the torrent will be saved in the current directory.
        """,
        "Have": """
        Command: Have [FTor] (Fo) (IPT)
        Description: Sends the specified torrent file to a tracker. You can provide a folder (Fo) and an optional tracker IP (IPT). If no IP is provided, the default tracker IP will be used.
        Example: Have mytorrent.torrent /myfolder 192.168.1.1
        """,
        "Down": """
        Command: Down [FTor] (Fo)
        Description: Downloads the file using the specified torrent. You can provide a folder (Fo) to store the file. If no tracker IP is provided, the default IP is used.
        Example: Down mytorrent.torrent /downloads 192.168.1.1
        """,
        "Preview": """
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


def generate_piece_hashes(file_path, piece_length):
    """Generates SHA-1 hashes for each piece of the file."""
    piece_hashes = b""
    with open(file_path, "rb") as f:
        while True:
            piece = f.read(piece_length)
            if not piece:
                break
            piece_hashes += hashlib.sha1(piece).digest()
    return piece_hashes


def make_torrent(file_path, output_folder=None, tracker_url=DEFAULT_TRACKER):
    """Creates a .torrent file from the given file."""
    if not os.path.exists(file_path):
        raise FileNotFoundError("The file does not exist.")

    piece_length = BLOCK_SZ * 1024  # 256 KB pieces, typical size for torrent files
    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)

    # Generate piece hashes
    piece_hashes = generate_piece_hashes(file_path, piece_length)

    tracker_url = DEFAULT_TRACKER
    print(tracker_url)
    print(DEFAULT_TRACKER)

    # Create the .torrent metadata structure
    torrent_data = {
        "announce": tracker_url,  # Tracker URL
        "info": {
            "name": file_name,
            "piece length": piece_length,
            "pieces": piece_hashes,
            "length": file_size,  # File size
        },
    }

    # Bencode the data
    bencoded_data = bencodepy.encode(torrent_data)

    # Save to output folder or current directory
    torrent_name = f"{file_name}.torrent"
    output_path = os.path.join(output_folder if output_folder else "", torrent_name)

    with open(output_path, "wb") as torrent_file:
        torrent_file.write(bencoded_data)

    print(f"Torrent file created: {output_path}")


# Main program loop


def main():
    welcome()  # Display the welcome message

    while True:
        user_input = input("Enter a command: ").strip()

        if user_input.lower() == "help":
            display_help_overview()  # Show concise help overview

        elif user_input.lower().startswith("help "):
            command = user_input.split()[1]
            # Show detailed help for the specific command
            display_command_help(command)

        elif user_input.lower().startswith("maketor "):
            # Split the input by spaces
            parts = user_input.split()

            # Initialize variables
            file_path = None
            tracker_url = None
            output_folder = None

            # Parse the command
            if len(parts) < 1:
                raise ValueError("Invalid input. Please provide at least the file path")

            # The first part is the command
            command = parts[0]

            # Expected parts: [command, file_path, output_folder (optional), tracker_url (optional)]
            file_path = parts[1]  # The second part is the file path
            output_folder = parts[2] if len(parts) > 2 else None
            tracker_url = parts[3] if len(parts) > 3 else None

            # Validate required parameters
            if not file_path:
                raise ValueError("File path is required.")

            make_torrent(file_path, output_folder, tracker_url)

        elif user_input.lower() == "exit":
            break

        else:
            print("Unknown command. Type 'Help' to see the list of available commands.")


# Run the program
if __name__ == "__main__":
    main()
