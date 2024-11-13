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
import math
import json
import threading
import time
import queue
import sys

from rich.live import Live
from rich.progress import Progress, BarColumn, TextColumn


write_lock = Lock()
debugLock = Lock()
download_queue = queue.Queue()
downloads = []
running = True
completed_downloads = []  # List to store completed downloads

# region Have
def send_torrent_tracker(torrent_file_path, tracker):    
    torrent_hash = trCtrl.get_torrent_hash(torrent_file_path)
    file_name = trCtrl.get_file_name(torrent_file_path)
    print(torrent_file_path)
    n = len(trCtrl.get_piece_hashes(torrent_file_path))

    if file_name not in fdt.get_all_files():
        if fdt.file_exists(file_name):
            fdt.add_file(file_name, [1] * n)
        else:
            fdt.add_file(file_name, [0] * n)
    
    if not fdt.file_exists(file_name):
        if file_name in fdt.get_all_files():
            fdt.update_array(file_name,[0]*n)

    tracker = trCtrl.get_trackers(torrent_file_path)[0]
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
                    full_path = full_path.replace("/", "\\")
                    send_torrent_tracker(full_path, tracker_url)
    elif file_path.endswith(".torrent"):
        # If it's a single .torrent file, process it directly
        file_path = f"program_{config.prog_num}/torrents/" + file_path
        send_torrent_tracker(file_path, tracker_url)
    else:
        print(f"No .torrent file found at: {file_path}")


# endregion


# region Upload
def peer_connect(client_socket):
    reponame = client_socket.recv(1024)
    filename = ""
    for repo in config.peer_repo:
        if repo["reponame"] == reponame:
            filename = repo["filename"]
    filename = f'program_{config.prog_num}/downloads/' + filename
    file_size = os.path.getsize(filename)
    piece_length = trCtrl.get_piece_length(file_size)
    print(f"Piece length: {piece_length}")
    # Print for another pear
    client_socket.send(("recievied_" + filename).encode())
    # client_socket.send(str(file_size).encode())
    print(filename)
    with client_socket.makefile("wb") as wfile:
        with open(filename, "rb") as f1:
            mm = mmap.mmap(f1.fileno(), 0, access=mmap.ACCESS_READ)
            while 1:
                torrent_file_name = client_socket.recv(1024).decode()
                if not torrent_file_name:
                    f1.close()
                    wfile.close()
                    client_socket.close()
                    return
                # print("recieved file name:")
                # print(trCtrl.get_file_name(torrent_file_name))

                # send DownloadedChunkBit Array
                fdt.update_data_file()
                data = json.dumps(
                    fdt.get_array(trCtrl.get_file_name(torrent_file_name))
                )
                client_socket.send(data.encode("utf-8"))

                a = client_socket.recv(4)
                offset = int.from_bytes(a, "big")
                mm.seek(offset * piece_length)
                data = mm.read(piece_length)
                byte_data = len(data).to_bytes(4, "big")
                client_socket.send(byte_data)
                wfile.write(data)
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


# endregion


# region Download
def download_chunk(
    progress,
    task,
    reponame,
    port,
    offset,
    piece_length,
    file_resu,
    key_value,
    total_size,
    offset_in_download_array,
    torrent_file_name,
):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    upload_host1 = socket.gethostbyname(socket.gethostname())
    client.connect((upload_host1, port))
    client.send(reponame)  # reponame la torrent hash
    file_name = client.recv(1024).decode()
    # file_size = client.recv(1024).decode()

    with client.makefile("rb") as rfile:
        with open(file_resu, "r+b") as f:
            mm = mmap.mmap(f.fileno(), 0)

            while 1:
                client.send(torrent_file_name.encode())
                trCtrl.get_file_name(torrent_file_name)
                # chunk_array=client.recv(1024).decode()
                data = client.recv(32768)  # DownloadedChunkBit Array
                chunk_array = json.loads(data.decode("utf-8"))
                # print(chunk_array)
                with write_lock:
                    # Check whether have full file
                    array = config.downloadArray[offset_in_download_array][
                        math.ceil(total_size / piece_length) : math.ceil(
                            total_size / piece_length
                        )
                        * 2
                    ]
                    if min(array) == 1:
                        if max(array) == 1:
                            client.close()
                            return

                    # update number of clients having each chunk
                    index = 0
                    while index < math.ceil(total_size / piece_length):
                        config.downloadArray[offset_in_download_array][index] += (
                            chunk_array[index]
                        )
                        index += 1

                while 1:
                    # Check whether have full file
                    array = config.downloadArray[offset_in_download_array][
                        math.ceil(total_size / piece_length) : math.ceil(
                            total_size / piece_length
                        )
                        * 2
                    ]
                    if min(array) == 1:
                        if max(array) == 1:
                            client.close()
                            return

                    # Find rarest chunk
                    with write_lock:
                        min_value = min(
                            config.downloadArray[offset_in_download_array][
                                0 : math.ceil(total_size / piece_length)
                            ]
                        )
                        value_chunk_of_downloader = config.downloadArray[
                            offset_in_download_array
                        ][
                            config.downloadArray[offset_in_download_array].index(
                                min_value
                            )
                            + math.ceil(total_size / piece_length)
                        ]
                        if value_chunk_of_downloader == 0:
                            if (
                                chunk_array[
                                    config.downloadArray[
                                        offset_in_download_array
                                    ].index(min_value)
                                ]
                                == 1
                            ):
                                config.downloadArray[offset_in_download_array][
                                    config.downloadArray[
                                        offset_in_download_array
                                    ].index(min_value)
                                    + math.ceil(total_size / piece_length)
                                ] = 2  # dang tai
                                offset = int(
                                    config.downloadArray[
                                        offset_in_download_array
                                    ].index(min_value)
                                )
                                break
                        if value_chunk_of_downloader == 1:
                            config.downloadArray[offset_in_download_array][
                                config.downloadArray[offset_in_download_array].index(
                                    min_value
                                )
                            ] = 1000000

                # send offset chunk
                byte_data = offset.to_bytes(4, "big")
                client.send(byte_data)
                # print(f"{file_name} - Chunk: {offset}")

                # receive required piece's length
                a = client.recv(4)
                byteDownload = int.from_bytes(a, "big")

                # receive data chunk
                data = rfile.read(byteDownload)
                ressu = hashlib.sha1(data).digest()
                # print(f"So byte doc: {len(data)}")
                # print(f'Data hex: {data.hex()}')
                # print(f"Hash Data ra: {ressu.hex()}")
                # print(f'Hash trong torrent: {key_value[offset].hex()}\n')


                # Check data with hash key
                if ressu == key_value[offset]:
                    with write_lock:
                        mm[offset * piece_length : (offset + 1) * piece_length] = data
                        progress.update(task,advance=1)
                        config.downloadArray[offset_in_download_array][
                            offset + math.ceil(total_size / piece_length)
                        ] = 1  # tai xong
                        fdt.update_data_file()
                        fdt.change_element(
                            trCtrl.get_file_name(torrent_file_name), offset, 1
                        )
                else:
                    # print("Received data does not match hash key\n")
                    with write_lock:
                        config.downloadArray[offset_in_download_array][
                            offset + math.ceil(total_size / piece_length)
                        ] = 0  # tai fail

                with write_lock:
                    # Check whether have full file
                    array = config.downloadArray[offset_in_download_array][
                        math.ceil(total_size / piece_length) : (
                            math.ceil(total_size / piece_length)
                            + math.ceil(total_size / piece_length)
                        )
                    ]
                    if min(array) == 1:
                        if max(array) == 1:
                            break
            mm.close()
            f.close()
    rfile.close()
    client.close()


def download(torrent_file_name, progress, tracker=None):
    # torrent = torrent_file_name
    torrent_file_name=f'program_{config.prog_num}/torrents/'+torrent_file_name
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
    num_of_piece = math.ceil(total_size / piece_length)
    # print(f"Piece length: {piece_length}")
    # print(f"File length: {total_size}")

    file_name = trCtrl.get_file_name(torrent_file_name)
    a = num_of_piece * 2
    task = progress.add_task(f"Download {file_name}", total=num_of_piece)
    downloads.append((file_name, task))

    # each downloader has specific offset_in_download_array
    with write_lock:
        config.downloadArray.append([0] * a)
        offset_in_download_array = config.offsetDownloader
        config.offsetDownloader += 1

    # add file into progress file with all 0 element
    fdt.update_data_file()
    if fdt.get_array(trCtrl.get_file_name(torrent_file_name)) is None:
        # Example Usage
        initial_data = [0] * num_of_piece
        fdt.add_file(trCtrl.get_file_name(torrent_file_name), initial_data)
    chunk_array = fdt.get_array(trCtrl.get_file_name(torrent_file_name))

    index = 0
    # print(offset_in_download_array)
    # print(num_of_piece)

    # assign to global array
    with write_lock:
        while index < num_of_piece:
            config.downloadArray[offset_in_download_array][num_of_piece + index] = (
                chunk_array[index]
            )
            index += 1
    # print(config.downloadArray[offset_in_download_array])

    file_resu = f"program_{config.prog_num}/downloads/" + trCtrl.get_file_name(
        torrent_file_name
    )
    os.makedirs(os.path.dirname(file_resu), exist_ok=True)
    with open(file_resu, "wb") as f:
        f.write(b"\x00" * total_size)

    offset = 0
    port_index = 0
    threads = []
    # print(port_list)

    while port_index < len(port_list) and port_index < 5:
        client_port = port_list[port_index]

        if int(client_port) == int(port):
            port_index += 1
            continue
        thread = Thread(
            target=download_chunk,
            args=(
                progress,
                task,
                torrent_hash,
                int(client_port),
                offset,
                piece_length,
                file_resu,
                key_value,
                total_size,
                offset_in_download_array,
                torrent_file_name,
            ),
        )
        thread.daemon = True
        threads.append(thread)

        thread.start()

        offset += 1
        port_index += 1

    for thread in threads:
        thread.join()

    client.close()
    # Check whether have full file
    array = config.downloadArray[offset_in_download_array][
        math.ceil(total_size / piece_length) : math.ceil(
            total_size / piece_length
        )
        * 2
    ]
    if min(array) == 1:
        if max(array) == 1:
            # have(torrent_file_name)
            # Now the task is complete, start the 30-second delay
            for remaining_time in range(10, 0, -1):
                progress.update(task, description=f"Moving {file_name} to completed in {remaining_time}s")
                time.sleep(1)

            # After the 30 seconds, remove the task from the progress bar and add it to completed list
            progress.remove_task(task)
            completed_downloads.append(f"Downloaded {file_name}")


# endregion


# region join/exit
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


# endregion

# Function to listen to user input commands and manage display
def input_listener(show_progress, live):
    hostname = config.DEFAULT_TRACKER
    join(hostname)
    print(f"Welcome user to ***'s bittorrent network,\nPeer ID: {config.peer_id} (OwO)")
    fdt.update_data_file()

    have(f"program_{config.prog_num}/torrents")
    
    while True:
        try:
            user_input = input("Enter a command: ").strip().lower()
            command_split = user_input.split()
            if user_input.startswith("down"):
                if len(command_split) != 2:
                    print("Note : fetch only accept 1 argument")
                else:
                    download_queue.put(command_split[1])
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
                # test-get_piece_hash <file torrent> <coi hash của piece số mấy>
                print(
                    trCtrl.get_piece_hashes(command_split[1])[
                        int(command_split[2])
                    ].hex()
                )
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
                file_path = f"program_{config.prog_num}/downloads/" + file_path
                output_folder = parts[2] if len(parts) > 2 else None
                tracker_url = parts[3] if len(parts) > 3 else None
                # Validate required parameters
                if not file_path:
                    raise ValueError("File path is required.")
                trCtrl.make_torrent(file_path, output_folder, tracker_url)
            elif user_input.lower() == "progress":
                show_progress[0] = True
                live.start()
                # Wait for any single key press to hide progress
                print("Press any key to hide progress...")
                get_keypress()  # Wait for any key press without Enter
                show_progress[0] = False
                live.stop()
            elif user_input.lower() == "completed":
                # Display completed downloads
                if completed_downloads:
                    print("Completed Downloads:")
                    for download in completed_downloads:
                        print(download)
                else:
                    print("No downloads completed yet in this.")
            elif user_input.lower() == "exit":
                client_exit(hostname)
                global running 
                running = False
                break

            else:
                print(
                    "Unknown command. Type 'Help' to see the list of available commands."
                )
        except Exception as e:
            print("Error: ", e)

# Function to manage and launch downloads
def download_manager(progress):
    while True:
        # Check for new download requests
        if not download_queue.empty():
            torName = download_queue.get()
            threading.Thread(target=download, args=(torName, progress), daemon=True).start()
        time.sleep(0.1)

# Check the platform to use appropriate key press detection
if sys.platform == "win32":
    import msvcrt
    def get_keypress():
        return msvcrt.getch()
else:
    import tty
    import termios
    def get_keypress():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def main():
    help.welcome()  # Display the welcome message

    # Initialize Progress and Live objects
    show_progress = [False]
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%")
    )
    live = Live(progress, refresh_per_second=4, transient=True)

    upload_thread = Thread(target=upload)
    # destroy this upload thread on quitting
    upload_thread.daemon = True
    upload_thread.start()

    # Start the download manager in a background thread
    threading.Thread(target=download_manager, args=(progress,), daemon=True).start()
    # Start the input listener in a background thread
    threading.Thread(target=input_listener, args=(show_progress, live), daemon=True).start()
    
    # Keep the main thread alive
    while running:
        if show_progress[0]:
            live.update(progress)  # Update live display when progress is shown
        time.sleep(1)


# Run the program
if __name__ == "__main__":
    port = 8000 + random.randint(0, 255)
    main()
