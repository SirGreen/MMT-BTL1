# Bittorrent Program Simulation
import os
import hashlib
import bencodepy  # For Bencoding (install using pip install bencodepy)
import socket
from threading import Thread
import random
import tqdm

DEFAULT_TRACKER = "http://hello.com"
Flag = False
peer_repo = []
SERVER_PORT = 7775
SERVER_HOST = "localhost"
BLOCK_SZ = 512
BLOCK = 128 << 10  # 128KB
BLOCK1 = 1 << 20  # 1024KB


def welcome():
    print("Welcome to a BitTorrent program by ***, press Help to see how to use")


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

def get_piece_length(total_size):
    """Determines the appropriate piece length based on total file size."""
    if total_size < 100 * 1024 * 1024:  # Less than 100 MB
        return 128 * 1024  # 128 KB
    elif total_size < 1 * 1024 * 1024 * 1024:  # Less than 1 GB
        return 256 * 1024  # 256 KB
    elif total_size < 5 * 1024 * 1024 * 1024:  # Less than 5 GB
        return 512 * 1024  # 512 KB
    else:
        return 1 * 1024 * 1024  # 1 MB

def make_torrent(file_path, output_folder=None, tracker_url=DEFAULT_TRACKER):
    if tracker_url is None:
        tracker_url = DEFAULT_TRACKER
    """Creates a .torrent file from the given file or directory."""
    if os.path.isdir(file_path):
        # If it's a directory, gather all files
        files = []
        total_size = 0
        
        for root, _, filenames in os.walk(file_path):
            for filename in filenames:
                full_path = os.path.join(root, filename)
                file_size = os.path.getsize(full_path)
                total_size += file_size
                relative_path = os.path.relpath(full_path, file_path)
                files.append({"length": file_size, "path": [relative_path]})  # Use list for path

        piece_length = get_piece_length(total_size)  # Determine piece length based on total size
    elif os.path.isfile(file_path):
        # Single file case
        files = []
        total_size = os.path.getsize(file_path)
        relative_path = os.path.basename(file_path)
        files.append({"length": total_size, "path": [relative_path]})  # Use list for path
        piece_length = get_piece_length(total_size)  # Determine piece length based on file size
    else:
        raise FileNotFoundError("The specified path does not exist.")

    # Generate piece hashes for all files
    piece_hashes = bytearray()
    if len(files)>1:
        for file_info in files:
            piece_hashes.extend(generate_piece_hashes(os.path.join(file_path, file_info["path"][0]), piece_length))
    else:
        piece_hashes.extend(generate_piece_hashes(file_path, piece_length))
    # Create the .torrent metadata structure
    torrent_data = {
        "announce": tracker_url,  # Tracker URL
        "info": {
            "name": os.path.basename(file_path) if os.path.isfile(file_path) else os.path.basename(os.path.normpath(file_path)),
            "piece length": piece_length,
            "pieces": bytes(piece_hashes),
            "files": files if len(files) > 1 else 1,  # Include files only if multiple
            "length": total_size if len(files) == 1 else "Not used for multiple files",  # Single file length
        },
    }

    # print(torrent_data)
    
    # Bencode the data
    bencoded_data = bencodepy.encode(torrent_data)

    # Save to output folder or current directory
    torrent_name = f"{os.path.basename(file_path)}.torrent"
    output_path = os.path.join(output_folder if output_folder else "", torrent_name)

    with open(output_path, "wb") as torrent_file:
        torrent_file.write(bencoded_data)

    print(f"Torrent file created: {output_path}")


def preview_torrent(torrent_file_path):
    """
    Parses and displays the contents of a .torrent file in a human-readable format.
    """
    if not os.path.exists(torrent_file_path):
        print(f"Error: The torrent file '{torrent_file_path}' does not exist.")
        return

    # Read and decode the torrent file
    try:
        with open(torrent_file_path, "rb") as f:
            torrent_data = bencodepy.decode(f.read())

        # Display the torrent contents in a readable format
        print("\n=== Torrent File Contents ===")
        for key, value in torrent_data.items():
            if isinstance(
                value, dict
            ):  # If it's a dictionary, print each key-value pair
                print(f"{key.decode('utf-8')}:")
                for sub_key, sub_value in value.items():
                    if isinstance(sub_value, int):
                        print(f"  {sub_key.decode('utf-8')}: {sub_value}")
                    elif sub_key.decode("utf-8") == "pieces":
                        print(
                            f"  {sub_key.decode('utf-8')}: {sub_value[:20].hex()}"
                            + ("..." if len(sub_value) > 20 else "")
                        )
                    elif isinstance(sub_value, list):
                        print(f"  {sub_key.decode('utf-8')}:")
                        for i, file_info in enumerate(sub_value, 1):
                            # Get length
                            length = file_info[b'length']
                            
                            # Get path and decode from bytes to string
                            path = file_info[b'path'][0].decode('utf-8')

                            # Print the formatted result
                            print(f"File {i}:")
                            print(f"  Path: {path}")
                            print(f"  Length: {length} bytes\n")
                    else:
                        print(
                            f"  {sub_key.decode('utf-8')}: {sub_value.decode('utf-8', errors='ignore')}"
                        )
            else:
                print(f"{key.decode('utf-8')}: {value.decode('utf-8', errors='ignore')}")
        print("\n=============================\n")

    except Exception as e:
        print(f"Error reading or decoding the torrent file: {e}")


def get_piece_hashes(torrent_file_path):
    """
    Returns a list of SHA-1 hashes of the pieces (chunks) stored in the .torrent file.

    :param torrent_file_path: Path to the .torrent file
    :return: List of SHA-1 hashes
    """
    if not os.path.exists(torrent_file_path):
        print(f"Error: The torrent file '{torrent_file_path}' does not exist.")
        return []

    try:
        with open(torrent_file_path, "rb") as f:
            torrent_data = bencodepy.decode(f.read())

        # Extract the 'pieces' field from the 'info' dictionary
        pieces = torrent_data[b"info"][b"pieces"]

        # Each SHA-1 hash is 20 bytes long, so we split the 'pieces' string accordingly
        hash_list = [pieces[i : i + 20] for i in range(0, len(pieces), 20)]

        # Return the list of hashes (in hexadecimal format for readability)
        return [hash.hex() for hash in hash_list]

    except Exception as e:
        print(f"Error reading or decoding the torrent file: {e}")
        return []


def send_requests(msg: str, server_host, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_host, server_port))
    client_socket.send(msg.encode())
    response = client_socket.recv(1024).decode()
    print(response)
    client_socket.close()
    return response


def peer_connect(client_socket):
    reponame = client_socket.recv(1024).decode()
    filename = ""
    for repo in peer_repo:
        if repo["reponame"] == reponame:
            filename = repo["filename"]
    file_size = os.path.getsize(filename)
    # Print for another pear
    client_socket.send(("recievied_" + filename).encode())
    client_socket.send(str(file_size).encode())
    with client_socket, client_socket.makefile("wb") as wfile:
        with open(filename, "rb") as f1:
            while data := f1.read(BLOCK):
                wfile.write(data)
        wfile.flush()
        f1.close()
    wfile.close()
    client_socket.close()


def upload():
    upload_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    upload_host = socket.gethostbyname(socket.gethostname())
    upload_socket.bind((upload_host, port))
    upload_socket.listen(5)
    while not Flag:
        (client_socket, client_addr) = upload_socket.accept()
        print("Got connection from", client_addr)
        new_thread = Thread(target=peer_connect, args=(client_socket,))
        new_thread.start()

    upload_socket.close()


def download(reponame):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    upload_host1 = socket.gethostbyname(socket.gethostname())
    msg = "FIND P2P-CI/1.0\nREPONAME:" + reponame
    send_requests(msg, "localhost", SERVER_PORT)
    #####
    port1 = int(input("Input peer port from list above: "))
    client.connect((upload_host1, port1))
    client.send(reponame.encode())
    file_name = client.recv(1024).decode()
    file_size = client.recv(1024).decode()
    print(file_name + " " + file_size)

    progress = tqdm.tqdm(
        unit="B", unit_scale=True, unit_divisor=1000, total=int(file_size)
    )
    with client.makefile("rb") as rfile:
        with open(file_name, "wb") as f:
            remaining = int(file_size)
            while remaining != 0:
                data = rfile.read(BLOCK1 if remaining > BLOCK1 else remaining)
                f.write(data)
                progress.update(len(data))
                remaining -= len(data)
        f.close()
    rfile.close()
    client.close()


def add(host):
    msg = "JOIN P2P-CI/1.0\nHost:" + host + "\n" + "Port:" + str(port)
    send_requests(msg, "localhost", SERVER_PORT)


def publish(host, title, filename):
    peer_repo.append({"filename": title, "reponame": filename})
    msg = (
        "PUBLISH RFC P2P-CI/1.0\nHost:"
        + host
        + "\n"
        + "Port:"
        + str(port)
        + "\n"
        + "File:"
        + title
        + "\n"
        + "Repo:"
        + filename
    )
    send_requests(msg, "localhost", SERVER_PORT)


def main():
    welcome()  # Display the welcome message

    upload_thread = Thread(target=upload)
    # destroy this upload thread on quitting
    upload_thread.daemon = True
    upload_thread.start()

    # ping_thread = Thread(target=recieve_ping)
    # ping_thread.daemon = True
    # ping_thread.start()

    hostname = input("Input your hostname: ")
    add(hostname)

    while True:
        user_input = input("Enter a command: ").strip().lower()
        command_split = user_input.split()

        if user_input.startswith("fetch"):
            if len(command_split) != 2:
                print("Note : fetch only accept 1 argument")
            else:
                download(command_split[1])
        elif user_input.startswith("publish"):
            if len(command_split) != 3:
                print("Note : publish only accept 2 argument")
            else:
                publish(hostname, command_split[1], command_split[2])
        # elif command_split[0] == 'find':
        #     if len(command_split) != 2:
        #         print("Note : publish only accept 1 argument")
        #     else:
        #         find(command_split[1])
        elif user_input == "help":
            display_help_overview()  # Show concise help overview
        elif user_input.startswith("help "):
            command = user_input.split()[1]
            # Show detailed help for the specific command
            display_command_help(command)
        elif user_input.startswith("preview"):
            preview_torrent(command_split[1])
        elif user_input.startswith("test-get_piece_hash "):
            # test getHash <file torrent> <coi hash của piece số mấy>
            print(get_piece_hashes(command_split[1])[int(command_split[2])])
        elif user_input.startswith("maketor "):
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
        elif user_input == "exit":
            exit(hostname)
            break

        else:
            print("Unknown command. Type 'Help' to see the list of available commands.")


# Run the program
if __name__ == "__main__":
    port = 8000 + random.randint(0, 255)
    main()
