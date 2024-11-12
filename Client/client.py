import mmap
import os
import hashlib
import socket
from threading import Lock, Thread
import tqdm
import help
import trComController as trCom
import random
import config
import torrentController as trCtrl
import atexit
import progress as fdt

write_lock = Lock()
debugLock = Lock()

#region Have
def send_torrent_tracker(torrent_file_path, tracker):
    torrent_hash = trCtrl.get_torrent_hash(torrent_file_path)
    print(torrent_file_path)
    n = len(trCtrl.get_piece_hashes(torrent_file_path))
    
    fdt.add_file(torrent_file_path,[False]*n)
    tracker = trCtrl.get_trackers(torrent_file_path)[0]
    file_name = trCtrl.get_file_name(torrent_file_path)
    config.peer_repo.append({"filename": file_name, "reponame": torrent_hash})
    print(file_name)
    params = {}
    params["torrent_hash"] = torrent_hash
    params["peerid"] = config.peer_id
    trCom.send_tracker("have", params, tracker)


def have(file_path, tracker_url=None):
    full_path = ""
    if os.path.isdir(file_path):
        # Walk through the directory and its subdirectories
        for root, dirs, files in os.walk(file_path):
            for file in files:
                # If the file ends with .torrent, process it
                if file.endswith(".torrent"):
                    full_path = os.path.join(root, file)
                    full_path = full_path.replace("/","\\")
                    send_torrent_tracker(
                        full_path, tracker_url
                    )  # Call the hypothetical send_to_tracker function
    elif file_path.endswith(".torrent"):
        # If it's a single .torrent file, process it directly
        file_path=f'program_{config.prog_num}/torrents/'+file_path
        send_torrent_tracker(file_path, tracker_url)
    else:
        print(f"No .torrent file found at: {file_path}")
#endregion

#region Upload
def peer_connect(client_socket):
    reponame = client_socket.recv(1024)
    filename = ""
    for repo in config.peer_repo:
        if repo["reponame"] == reponame:
            filename = repo["filename"]
    file_size = os.path.getsize(filename)
    piece_length = trCtrl.get_piece_length(file_size)
    print(f"Piece length: {piece_length}")
    # Print for another pear
    client_socket.send(("recievied_" + filename).encode())
    client_socket.send(str(file_size).encode())
    #gui Dict[reponame]
    with client_socket, client_socket.makefile("wb") as wfile:
        with open(filename, "rb") as f1:
            mm = mmap.mmap(f1.fileno(), 0, access=mmap.ACCESS_READ)
            a = client_socket.recv(4)
            offset = int.from_bytes(a, "big")
            mm.seek(offset * piece_length)
            data = mm.read(piece_length)
            ressu = hashlib.sha1(data).digest()
            # print(f'Data: {data.hex()}')
            print(f"Hash ra: {ressu.hex()}")
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
    while not config.Flag:
        (client_socket, client_addr) = upload_socket.accept()
        print("Got connection from", client_addr)
        new_thread = Thread(target=peer_connect, args=(client_socket,))
        new_thread.start()

    upload_socket.close()
#endregion

#region Download
def download_chunk(
    port_list, reponame, port, offset, piece_length, file_resu, key_value, total_size
):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    upload_host1 = socket.gethostbyname(socket.gethostname())
    client.connect((upload_host1, port))
    client.send(reponame) #reponame la torrent hash
    file_name = client.recv(1024).decode()
    file_size = client.recv(1024).decode()
    #TODO
    #Nhan list bool
    print(file_name)
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
            print(
                f"So byte doc: {piece_length if total_size > piece_length else total_size}"
            )
            # print(f'Data hex: {data.hex()}')
            print(f"Hash Data ra: {ressu.hex()}")
            print(key_value[offset].hex())
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


def download(torrent_file_name, tracker=None):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    torrent_hash = trCtrl.get_torrent_hash(torrent_file_name)
    if tracker is None:
        tracker = config.DEFAULT_TRACKER
    url = tracker + "/announce/down"
    params = {}
    params["torrent_hash"] = trCtrl.get_torrent_hash(torrent_file_name)
    params["peerid"] = config.peer_id
    port_list = trCom.send_get(url, params).json()
    #####
    # port1 = int(input("Input peer port from list above: "))
    key_value = trCtrl.get_piece_hashes(torrent_file_name)
    total_size = trCtrl.get_file_length(torrent_file_name)
    piece_length = trCtrl.get_piece_length(total_size)
    print(f"Piece length: {piece_length}")
    print(f"Piece length: {total_size}")
    offset = 0
    port_index = 0

    file_resu = f"program_{config.prog_num}/downloads/" + trCtrl.get_file_name(torrent_file_name)
    os.makedirs(os.path.dirname(file_resu), exist_ok=True)
    with open(file_resu, "wb") as f:
        f.write(b"\x00" * total_size)
    #TODO
    #dict key torrent_hash = [False]*len(key_value)
    threads = []
    print(port_index)
    while offset < len(key_value):
        client_port = port_list[port_index]

        thread = Thread(
            target=download_chunk,
            args=(
                port_list,
                torrent_hash,
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
#endregion

#region join/exit
def get_program_number():
    running_file = "running.txt"
    program_numbers = set()
    
    # Check if 'running.txt' exists and read the program numbers
    if os.path.exists(running_file):
        with open(running_file, "r") as f:
            for line in f:
                try:
                    # Extract program numbers from each line
                    program_numbers.add(int(line.strip()))
                except ValueError:
                    continue

    # Find the next available program number
    num = 1
    while num in program_numbers:
        num += 1
    return num

def cleanup(program_number):
    # Remove the program number from 'running.txt' when exiting
    running_file = "running.txt"
    if os.path.exists(running_file):
        with open(running_file, "r") as f:
            lines = f.readlines()
        
        # Rewrite 'running.txt' without the current program number
        with open(running_file, "w") as f:
            for line in lines:
                if line.strip() != str(program_number):
                    f.write(line)

def setup_program_folder():
    # Get the designated program number
    program_number = get_program_number()
    program_folder = f"program_{program_number}"
    
    # Create the program folder and subfolders if they don't exist
    if not os.path.exists(program_folder):
        os.makedirs(os.path.join(program_folder, "torrents"))
        os.makedirs(os.path.join(program_folder, "downloads"))
    
    # Append the program number to the central 'running.txt' to signal it's running
    with open("running.txt", "a") as f:
        f.write(f"{program_number}\n")

    # Register cleanup function to remove the program number on exit
    atexit.register(cleanup, program_number)

    return program_number



def join(tracker=None):
    config.prog_num = setup_program_folder()
    config.peer_id = config.peer_id + str(config.prog_num)
    if tracker is None:
        tracker = config.DEFAULT_TRACKER
    url = tracker + "/announce/join"
    params = {}
    params["peerid"] = config.peer_id
    params["port"] = port
    trCom.send_get(url, params)


def client_exit(tracker=None):
    if tracker is None:
        tracker = config.DEFAULT_TRACKER
    url = tracker + "/announce/exit"
    params = {}
    params["peerid"] = config.peer_id
    print(config.peer_id)
    trCom.send_get(url, params)
#endregion

def main():
    help.welcome()  # Display the welcome message

    upload_thread = Thread(target=upload)
    # destroy this upload thread on quitting
    upload_thread.daemon = True
    upload_thread.start()

    # ping_thread = Thread(target=recieve_ping)
    # ping_thread.daemon = True
    # ping_thread.start()

    hostname = config.DEFAULT_TRACKER
    join(hostname)
    print(f"Welcome user to ***'s bittorrent network,\nPeer ID: {config.peer_id} (OwO)")
    fdt.update_data_file()
    
    have(f'program_{config.prog_num}/torrents')
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
                trCtrl.preview_torrent(command_split[1])
            elif user_input.startswith("have"):
                if len(command_split) > 2:
                    have(command_split[1], command_split[2])
                else:
                    have(command_split[1])
            elif user_input.startswith("test-get_piece_hash "):
                # test getHash <file torrent> <coi hash của piece số mấy>
                print(trCtrl.get_piece_hashes(command_split[1])[int(command_split[2])].hex())
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
                trCtrl.make_torrent(file_path, output_folder, tracker_url)
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
