# Bittorrent Program Simulation
import mmap
import os
import hashlib
import bencodepy  # For Bencoding (install using pip install bencodepy)
import socket
from threading import Lock, Thread
import tqdm
import help
import trComController as trCom
import random
from config import peer_id, DEFAULT_TRACKER, peer_repo, Flag

write_lock = Lock()
# region Piece&Torrent
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
                files.append(
                    {"length": file_size, "path": [relative_path]}
                )  # Use list for path

        piece_length = get_piece_length(
            total_size
        )  # Determine piece length based on total size
    elif os.path.isfile(file_path):
        # Single file case
        files = []
        total_size = os.path.getsize(file_path)
        relative_path = os.path.basename(file_path)
        files.append(
            {"length": total_size, "path": [relative_path]}
        )  # Use list for path
        piece_length = get_piece_length(
            total_size
        )  # Determine piece length based on file size
    else:
        raise FileNotFoundError("The specified path does not exist.")

    # Generate piece hashes for all files
    piece_hashes = bytearray()
    if len(files) > 1:
        for file_info in files:
            piece_hashes.extend(
                generate_piece_hashes(
                    os.path.join(file_path, file_info["path"][0]), piece_length
                )
            )
    else:
        piece_hashes.extend(generate_piece_hashes(file_path, piece_length))
    # Create the .torrent metadata structure
    torrent_data = {
        "announce": tracker_url,  # Tracker URL
        "info": {
            "name": os.path.basename(file_path)
            if os.path.isfile(file_path)
            else os.path.basename(os.path.normpath(file_path)),
            "piece length": piece_length,
            "pieces": bytes(piece_hashes),
            "files": files if len(files) > 1 else 1,  # Include files only if multiple
            "length": total_size
            if len(files) == 1
            else "Not used for multiple files",  # Single file length
        },
    }

    # print(torrent_data)

    # Bencode the data
    bencoded_data = bencodepy.encode(torrent_data)

    # Save to output folder or current directory
    torrent_name = f"{os.path.splitext(os.path.basename(file_path))[0]}.torrent"
    output_path = os.path.join(output_folder if output_folder else "", torrent_name)

    with open(output_path, "wb") as torrent_file:
        torrent_file.write(bencoded_data)

    print(f"Torrent file created: {output_path}")

    return output_path


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
                            length = file_info[b"length"]

                            # Get path and decode from bytes to string
                            path = file_info[b"path"][0].decode("utf-8")

                            # Print the formatted result
                            print(f"File {i}:")
                            print(f"  Path: {path}")
                            print(f"  Length: {length} bytes\n")
                    else:
                        print(
                            f"  {sub_key.decode('utf-8')}: {sub_value.decode('utf-8', errors='ignore')}"
                        )
            else:
                print(
                    f"{key.decode('utf-8')}: {value.decode('utf-8', errors='ignore')}"
                )
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
        return [hash for hash in hash_list]

    except Exception as e:
        print(f"Error reading or decoding the torrent file: {e}")
        return []

# endregion
def get_file_object(filename, mode='r'):
    """Open a file and return the file object."""
    try:
        file_object = open(filename, mode)
        return file_object
    except FileNotFoundError:
        print(f"Error: The file '{filename}' was not found.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def get_torrent_hash(torrent_file_path):
    if not os.path.exists(torrent_file_path):
        raise FileNotFoundError(
            f"The torrent file '{torrent_file_path}' does not exist."
        )

    hasher = hashlib.sha1()
    with open(torrent_file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.digest()

def send_torrent_tracker(torrent_file_path, tracker):
    torrent_hash=get_torrent_hash(torrent_file_path)
    peer_repo.append({"filename": torrent_file_path, "reponame": torrent_file_path})
    params={}
    params['port']=port
    params['torrent_hash']=torrent_hash
    params['peerid']=peer_id
    trCom.send_tracker("have",params)

def have(file_path, tracker_url=None):
    tracker_url = tracker_url if tracker_url else DEFAULT_TRACKER
    full_path = ""
    if os.path.isdir(file_path):
        # Walk through the directory and its subdirectories
        for root, dirs, files in os.walk(file_path):
            for file in files:
                # If the file ends with .torrent, process it
                if file.endswith(".torrent"):
                    full_path = os.path.join(root, file)
                    send_torrent_tracker(
                        full_path, tracker_url
                    )  # Call the hypothetical send_to_tracker function
    elif file_path.endswith(".torrent"):
        # If it's a single .torrent file, process it directly
        send_torrent_tracker(file_path, tracker_url)
    else:
        print(f"No .torrent file found at: {file_path}")

def peer_connect(client_socket):
    reponame = client_socket.recv(1024).decode()
    filename = ""
    print(peer_repo)
    for repo in peer_repo:
        if repo["reponame"] == reponame:
            filename = repo["filename"]
    file_size = os.path.getsize(filename)
    piece_length = get_piece_length(file_size)
    # Print for another pear
    client_socket.send(("recievied_" + filename).encode())
    client_socket.send(str(file_size).encode())
    with client_socket, client_socket.makefile("wb") as wfile:
        with open(filename, "rb") as f1:
            mm = mmap.mmap(f1.fileno(), 0, access=mmap.ACCESS_READ)
            a = client_socket.recv(4)
            offset = int.from_bytes(a, "big")
            mm.seek(offset * piece_length)
            # data= mm.read(offset,piece_length)
            data = mm.read(piece_length)
            ressu = hashlib.sha1(data).digest()
            print(ressu)
            print(offset)
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


def download_chunk(
    port_list, reponame, port, offset, piece_length, file_resu, key_value, total_size
):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    upload_host1 = socket.gethostbyname(socket.gethostname())

    client.connect((upload_host1, port))
    client.send(reponame.encode())
    file_name = client.recv(1024).decode()
    file_size = client.recv(1024).decode()
    if port == port_list[0]:
        print(file_name + " " + file_size)

    # remaining = total_size - (offset * piece_length)

    progress = tqdm.tqdm(
        unit="B",
        unit_scale=True,
        unit_divisor=1000,
        total=int(piece_length if total_size > piece_length else total_size),
    )
    with client.makefile("rb") as rfile:
        with open(file_resu, "r+b") as f:
            # Memory-map the file
            mm = mmap.mmap(f.fileno(), 0)
            # while remaining != 0:
            byte_data = offset.to_bytes(4, "big")
            client.send(byte_data)
            print(offset)
            data = rfile.read(piece_length if total_size > piece_length else total_size)
            ressu = hashlib.sha1(data).digest()
            print(ressu)
            print(key_value[offset])
            if ressu == key_value[offset]:
                with write_lock:
                    mm[offset * piece_length : (offset + 1) * piece_length] = data
                    progress.update(len(data))
                    total_size -= len(data)
            else:
                print("meo")
            mm.close()
            f.close()
    rfile.close()
    client.close()


def download(reponame, tracker=None):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    if tracker is None:
        tracker = DEFAULT_TRACKER
    url = tracker+"/announce/down"
    params={}
    params['torrent_hash']=get_torrent_hash(reponame)
    params['peerid']=peer_id
    params['port']=port
    port_list = trCom.send_get(url,params).json()
    #####
    # port1 = int(input("Input peer port from list above: "))
    file_path = os.path.abspath(reponame)
    key_value = get_piece_hashes(make_torrent(file_path))
    total_size = os.path.getsize(file_path)
    piece_length = get_piece_length(total_size)

    offset = 0
    port_index = 0

    file_resu = reponame
    with open(file_resu, "wb") as f:
        f.write(b"\x00" * total_size)

    threads = []
    print(port_index)
    while offset < len(key_value):
        client_port = port_list[port_index]

        thread = Thread(
            target=download_chunk,
            args=(
                port_list,
                reponame,
                int(client_port),
                offset,
                piece_length,
                file_resu,
                key_value,
                total_size,
            ),
        )
        thread.daemon = True
        threads.append(thread)

        thread.start()

        offset += 1
        port_index += 1

        if port_index >= len(port_list):
            port_index = 0

    for thread in threads:
        thread.join()

    client.close()

def join(tracker=None):
    if tracker is peer_id:
        tracker = DEFAULT_TRACKER
    url = tracker+"/announce/join"
    params={}
    params['peerid']=peer_id
    trCom.send_get(url,params)

def client_exit(tracker=None):
    if tracker is peer_id:
        tracker = DEFAULT_TRACKER
    url = tracker+"/announce/exit"
    params={}
    params['peerid']=peer_id
    trCom.send_get(url,params)


def main():
    help.welcome()  # Display the welcome message

    upload_thread = Thread(target=upload)
    # destroy this upload thread on quitting
    upload_thread.daemon = True
    upload_thread.start()

    # ping_thread = Thread(target=recieve_ping)
    # ping_thread.daemon = True
    # ping_thread.start()

    hostname = peer_id
    print(f"Welcome user to ***'s bittorrent network,\nPeer ID: {hostname} (OwO)")
    join(hostname)
    while True:
        try:
            user_input = input("Enter a command: ").strip().lower()
            command_split = user_input.split()
            if user_input.startswith("down"):
                if len(command_split) != 2:
                    print("Note : fetch only accept 1 argument")
                else:
                    download(command_split[1])
            # elif command_split[0] == 'find':
            #     if len(command_split) != 2:
            #         print("Note : publish only accept 1 argument")
            #     else:
            #         find(command_split[1])
            elif user_input == "help":
                help.display_help_overview()  # Show concise help overview
            elif user_input.startswith("help "):
                command = user_input.split()[1]
                # Show detailed help for the specific command
                help.display_command_help(command)
            elif user_input.startswith("preview"):
                preview_torrent(command_split[1])
            elif user_input.startswith("have"):
                if len(command_split) > 2:
                    have(command_split[1], command_split[2])
                else:
                    have(command_split[1])
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
                    raise ValueError(
                        "Invalid input. Please provide at least the file path"
                    )
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
                client_exit(hostname)
                break

            else:
                print(
                    "Unknown command. Type 'Help' to see the list of available commands."
                )
        except Exception as e:
            print("Error: ", e)


# Run the program
if __name__ == "__main__":
    port = 8000 + random.randint(0, 255)
    main()
