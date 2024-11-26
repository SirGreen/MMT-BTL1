import mmap
import os
import hashlib
import socket
from threading import Lock, Thread
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
from rich.console import Console
import re

from rich.live import Live
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    DownloadColumn,
    TaskProgressColumn,
)


write_lock = Lock()
debugLock = Lock()
download_queue = queue.Queue()
downloads = []
running = True
console = Console()


def printAnnounce(msg):
    print(msg + "\nEnter a command: ")


# region Have
def send_torrent_tracker(torrent_file_path, tracker):
    torrent_hash = trCtrl.get_torrent_hash(torrent_file_path)
    file_name = trCtrl.get_file_name(torrent_file_path)
    print(f"Sending tracker: {torrent_file_path}")
    n = len(trCtrl.get_piece_hashes(torrent_file_path))

    fdt.update_data_file(file_name, n)

    # tracker = trCtrl.get_trackers(torrent_file_path)[0]
    tracker = config.DEFAULT_TRACKER
    config.peer_repo.append({"filename": file_name, "reponame": torrent_hash})
    # print(file_name)
    params = {}
    params["torrent_hash"] = torrent_hash
    params["peerid"] = config.peer_id
    if fdt.file_downloaded(file_name):
        trCom.send_tracker("done", params, tracker)
    else:
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

# region Scrape


def send_scrape(torrent_file_path, tracker):
    torrent_hash = trCtrl.get_torrent_hash(torrent_file_path)
    file_name = trCtrl.get_file_name(torrent_file_path)

    tracker = config.DEFAULT_TRACKER
    config.peer_repo.append({"filename": file_name, "reponame": torrent_hash})
    print(file_name)
    params = {}
    params["torrent_hash"] = torrent_hash
    params["peerid"] = config.peer_id
    response = trCom.send_tracker("scrape", params, tracker)
    print(response.text)
    # url = tracker + "/announce/scrape"
    # trCom.send_get(url, params)


def scrape(file_path, tracker_url=None):
    full_path = ""
    if os.path.isdir(file_path):
        # Walk through the directory and its subdirectories
        for root, dirs, files in os.walk(file_path):
            for file in files:
                # If the file ends with .torrent, process it
                if file.endswith(".torrent"):
                    full_path = os.path.join(root, file)
                    full_path = full_path.replace("/", "\\")
                    send_scrape(full_path, tracker_url)
    elif file_path.endswith(".torrent"):
        # If it's a single .torrent file, process it directly
        file_path = f"program_{config.prog_num}/torrents/" + file_path
        send_scrape(file_path, tracker_url)
    else:
        print(f"No .torrent file found at: {file_path}")


# endregion


# region Upload
def peer_connect(client_socket):
    try:
        downType = client_socket.recv(1024).decode()
        if downType == "Torrent file":
            client_socket.send(("Downloading torrent...").encode())
            reponame = client_socket.recv(1024) 
            filename = ""
            for repo in config.peer_repo:
                if repo["reponame"] == reponame:
                    filename = repo["filename"]
            filename = os.path.splitext(filename)[0]+".torrent"
            client_socket.send(filename.encode())
            filename = f"program_{config.prog_num}/torrents/" + filename
            try:
                # Open the .torrent file and send its contents
                with open(filename, 'rb') as file:
                    while chunk := file.read(1024):
                        client_socket.sendall(chunk)
                print("File sent successfully.")
            except FileNotFoundError:
                print("File not found. Ensure the .torrent file exists.")
            return
        
        client_socket.send(("OK!").encode())
        reponame = client_socket.recv(1024)
        filename = ""
        for repo in config.peer_repo:
            if repo["reponame"] == reponame:
                filename = repo["filename"]
        filename = f"program_{config.prog_num}/downloads/" + filename
        # file_size = os.path.getsize(filename)
        piece_length = 0
        client_socket.send(("recievied_" + filename).encode())
        # client_socket.send(str(file_size).encode())
        print(filename)
        first = True
        while not os.path.exists(filename):
            time.sleep(1)
        with client_socket.makefile("wb") as wfile:
            with open(filename, "rb") as f1:
                mm = mmap.mmap(f1.fileno(), 0, access=mmap.ACCESS_READ)
                while 1:
                    torrent_file_name = None
                    try:
                        torrent_file_name = client_socket.recv(1024).decode()
                    except Exception as e:
                        1
                    
                    if not torrent_file_name:
                        # f1.close()
                        # wfile.close()
                        # client_socket.close()
                        # return
                        break
                    
                    elif first:
                        first = False
                        torrent_file_name = os.path.basename(torrent_file_name)
                        torrent_file_name = (
                            f"program_{config.prog_num}/torrents/" + torrent_file_name
                        )
                        piece_length = trCtrl.get_piece_length_from_torrent(
                            torrent_file_name
                        )
                        # print(f"Piece length: {piece_length}")
                        
                    torrent_file_name = os.path.basename(torrent_file_name)
                    torrent_file_name = (
                        f"program_{config.prog_num}/torrents/" + torrent_file_name
                    )
                    # print("recieved file name:")
                    # print(trCtrl.get_file_name(torrent_file_name))

                    # send DownloadedChunkBit Array
                    fdt.update_data_file_dir()
                    data = json.dumps(
                        fdt.get_array(trCtrl.get_file_name(torrent_file_name))
                    )
                    client_socket.send(data.encode("utf-8"))
                    try:
                        a = client_socket.recv(4)
                    except Exception as e:
                        # print(f"Connection aborted: {e}")
                        1
                        
                    offset = int.from_bytes(a, "big")
                    mm.seek(offset * piece_length)
                    data = mm.read(piece_length)
                    byte_data = len(data).to_bytes(4, "big")
                    try:
                        client_socket.send(byte_data)
                    except Exception as e:
                        1
                    try:
                        wfile.write(data)
                    except Exception as e:
                        1
            f1.close()
        wfile.close()
        client_socket.close()
    except Exception as e:
        1


def upload():
    upload_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    upload_host = socket.gethostbyname(socket.gethostname())
    upload_socket.bind((upload_host, port))
    upload_socket.listen(5)
    while not config.Flag:
        try:
            (client_socket, client_addr) = upload_socket.accept()
            print("Got connection from", client_addr)
            new_thread = Thread(target=peer_connect, args=(client_socket,))
            new_thread.start()
        except Exception as e:
            1

    upload_socket.close()


# endregion

def find_zero_indices(arr):
    return [i for i, value in enumerate(arr) if value == 0]

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
    client_ip,
):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # upload_host1 = socket.gethostbyname(socket.gethostname())
        # print(f'Debug connect: {upload_host1}, {port}')
        client.connect((client_ip, port))
        client.send("Chunk".encode())
        client.recv(1024)
        client.send(reponame)  # reponame la torrent hash
        file_name = client.recv(1024).decode()
        # file_size = client.recv(1024).decode()

        with client.makefile("rb") as rfile:
            with open(file_resu, "r+b") as f:
                mm = mmap.mmap(f.fileno(), 0)
                chunk_array = []
                while 1:
                    start_index=0
                    client.send(torrent_file_name.encode())
                    trCtrl.get_file_name(torrent_file_name)
                    # chunk_array=client.recv(1024).decode()
                    data = client.recv(32768)  # DownloadedChunkBit Array
                    try:
                        json_buffer = json.loads(data.decode("utf-8"))
                        chunk_array = json_buffer
                    except Exception as e:
                        client.close()
                        download_chunk(progress,
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
                            client_ip)
                    chunk_array = chunk_array
                    # with write_lock:
                    #     # Check whether have full file
                    #     array = config.downloadArray[offset_in_download_array][
                    #         math.ceil(total_size / piece_length) : math.ceil(
                    #             total_size / piece_length
                    #         )
                    #         * 2
                    #     ]
                    #     if min(array) == 1:
                    #         if max(array) == 1:
                    #             client.close()
                    #             return
                    num_of_piece=math.ceil(total_size / piece_length)
                    # print(chunk_array)
                    
                    # with write_lock:
                    #     # Check whether have full file
                    #     array = config.downloadArray[offset_in_download_array][
                    #         math.ceil(total_size / piece_length) : math.ceil(
                    #             total_size / piece_length
                    #         )
                    #         * 2
                    #     ]
                    # if all(chunk == 1 for chunk in array):
                    #         # if max(array) == 1:
                    #             client.close()
                    #             return

                        # update number of clients having each chunk
                    with write_lock:
                        index = 0
                        while index < num_of_piece:
                            config.downloadArray[offset_in_download_array][index] += (
                                chunk_array[index]
                            )
                            index += 1

                    while 1:
                        array_at_offset=config.downloadArray[offset_in_download_array]
                        # Check whether have full file
                        array = array_at_offset[
                            num_of_piece : num_of_piece* 2
                        ]
                        if all(chunk == 1 for chunk in array):
                            # if max(array) == 1:
                                client.close()
                                return

                        # Find rarest chunk
                        min_value = min(
                                array_at_offset[
                                    start_index : num_of_piece
                                ]
                        )
                        
                        index_of_min_value= array_at_offset.index(
                                min_value
                        )
                           
                        start_index=index_of_min_value + 1 
                        if start_index >= num_of_piece:
                            start_index=0
                                
                        with write_lock:  
                            value_chunk_of_downloader = config.downloadArray[offset_in_download_array][
                                index_of_min_value
                                + num_of_piece
                            ]  
                            if value_chunk_of_downloader == 0:
                                if (
                                    chunk_array[
                                        index_of_min_value
                                    ]
                                    == 1
                                ):
                                    config.downloadArray[offset_in_download_array][
                                        index_of_min_value
                                        + num_of_piece
                                    ] = 2  # dang tai
                                    offset = int(
                                        index_of_min_value
                                    )
                                    break
                            if value_chunk_of_downloader == 1:
                                config.downloadArray[offset_in_download_array][
                                    index_of_min_value
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
                            mm[offset * piece_length : (offset + 1) * piece_length] = (
                                data
                            )
                            config.bytesDownload[offset_in_download_array] += (
                                piece_length / (1024 * 1024)
                            )
                            progress.update(task, advance=piece_length)

                            # console.print(
                            #     f"[yellow]Speed: {config.bytesDownload[offset_in_download_array]/(time.time()-config.timeStartDownload[offset_in_download_array]):.2f} MB/s[/yellow]",
                            #     end="\r",
                            # )
                            config.downloadArray[offset_in_download_array][
                                offset + math.ceil(total_size / piece_length)
                            ] = 1  # tai xong
                            config.downloadArray[offset_in_download_array][
                                offset
                            ] = 1000000
                            fdt.update_data_file_dir()
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
                            num_of_piece : (
                                num_of_piece*2
                            )
                        ]
                    if all(chunk == 1 for chunk in array):
                            # if max(array) == 1:
                               break
                mm.close()
            f.close()
        rfile.close()
        client.close()
    except Exception as e:
        # print(e)
        1


def download(torrent_file_name, progress, tracker=None):
    try:
        # torrent = torrent_file_name
        torrent_file_name = f"program_{config.prog_num}/torrents/" + torrent_file_name
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        torrent_hash = trCtrl.get_torrent_hash(torrent_file_name)
        if tracker is None:
            tracker = config.DEFAULT_TRACKER
        url = tracker + "/announce/down"
        params = {}
        params["torrent_hash"] = trCtrl.get_torrent_hash(torrent_file_name)
        params["peerid"] = config.peer_id
        port_list = trCom.send_get(url, params).json()
        # print(port_list)
        #####
        
        config.peer_repo.append({"filename": trCtrl.get_file_name(torrent_file_name), "reponame": torrent_hash})
        
        # port1 = int(input("Input peer port from list above: "))
        key_value = trCtrl.get_piece_hashes(torrent_file_name)
        total_size = trCtrl.get_file_length(torrent_file_name)
        piece_length = trCtrl.get_piece_length_from_torrent(torrent_file_name)
        num_of_piece = math.ceil(total_size / piece_length)
        # print(f"Piece length: {piece_length}")
        # print(f"File length: {total_size}")

        file_name = trCtrl.get_file_name(torrent_file_name)
        fdt.update_data_file(file_name, num_of_piece)
        if fdt.file_downloaded(file_name) == 1:
            printAnnounce("This file is already downloaded, remove it to redownload")
            return
        a = num_of_piece * 2

        # each downloader has specific offset_in_download_array
        with write_lock:
            config.downloadArray.append([0] * a)
            config.bytesDownload.append(0)
            config.timeStartDownload.append(time.time())
            offset_in_download_array = config.offsetDownloader
            config.offsetDownloader += 1

        # add file into progress file with all 0 element
        fdt.update_data_file_dir()
        if fdt.get_array(trCtrl.get_file_name(torrent_file_name)) is None:
            # Example Usage
            initial_data = [0] * num_of_piece
            fdt.add_file(trCtrl.get_file_name(torrent_file_name), initial_data)
        chunk_array = fdt.get_array(trCtrl.get_file_name(torrent_file_name))

        num_of_piece_left = 0
        for x in chunk_array:
            if x == 0:
                num_of_piece_left = num_of_piece_left + 1
        
        task = progress.add_task(f"Download {file_name}", total=num_of_piece * piece_length)
        progress.update(task, advance=(num_of_piece - num_of_piece_left) * piece_length)
        
        for fn, ts in downloads:
            print(fn)
            if fn==file_name and ts!=task:
                downloads.remove((fn,ts))
                progress.remove_task(ts)
        downloads.append((file_name, task))
        

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
        if all(x == 0 for x in chunk_array):
            with open(file_resu, "wb") as f:
                f.write(b"\x00" * total_size)

        offset = 0
        port_index = 0
        threads = []
        # print(port_list)

        while port_index < len(port_list) and port_index < 5:
            client_port = port_list[port_index][1]
            client_ip = port_list[port_index][0]
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
                    client_ip,
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
            math.ceil(total_size / piece_length) : math.ceil(total_size / piece_length) * 2
        ]
        if all(chunk == 1 for chunk in array):
            # if max(array) == 1:
                # have(torrent_file_name)
                # Now the task is complete, start the 30-second delay
                trCom.send_tracker("done", params, tracker)
                
        for remaining_time in range(10, 0, -1):
            progress.update(
                task,
                description=f"Moving {file_name} to completed in {remaining_time}s",
            )
            time.sleep(1)

        # After the 10 seconds, remove the task from the progress bar and add it to completed list
        progress.remove_task(task)
        downloads.remove((file_name, task))
    except Exception as e:
        # print(e)
        1


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
    params["IP"] = socket.gethostbyname(socket.gethostname())
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

# region ping


def ping_tracker(tracker=None):
    if tracker is None:
        tracker = config.DEFAULT_TRACKER
    url = tracker + "/announce/ping"
    params = {}
    params["peerid"] = config.peer_id

    while not config.Flag:
        # trCom.send_get(url, params)
        print("Ping sent to tracker")
        rep = trCom.send_get(url, params)
        if rep is None:
            print("No tracker connected.")
        else:
            if rep.text != "OK!":
                print("Tracker offline!!!")
            # else:
            #     print("Tracker say hi!")

        # print(f"{type(trCom.send_get(url, params))}")
        time.sleep(1798)  # 30p 1798


# endregion


#region Main Helper
# Function to listen to user input commands and manage display
def input_listener(show_progress, live):
    hostname = config.DEFAULT_TRACKER
    join(hostname)
    print(f"Welcome user to DDTorrent's bittorrent network,\nPeer ID: {config.peer_id} (OwO)")
    fdt.update_data_file_dir()

    ping_thread = Thread(target=ping_tracker, args=(hostname,))
    ping_thread.daemon = True
    ping_thread.start()

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
            elif user_input.startswith("scrape"):
                if len(command_split) > 2:
                    scrape(command_split[1], command_split[2])
                else:
                    scrape(command_split[1])
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
                if len(downloads) == 0:
                    print(
                        "Download queue is empty. Waiting for a downloads to start or for a key press..."
                    )
                else:
                    print("Press any key to hide progress....")

                while len(downloads) == 0 and not msvcrt.kbhit():
                    time.sleep(0.1)

                # If the user presses a key, proceed with hiding progress
                if msvcrt.kbhit():
                    msvcrt.getch()
                    print("Key pressed. Hiding progress...")
                    continue

                if len(downloads) != 0:
                    show_progress[0] = True
                    live.start()
                    get_keypress()  # Wait for any key press without Enter
                    print("Press any key to hide progress...")
                    show_progress[0] = False
                    live.stop()
            elif user_input.lower() == "status":
                files = fdt.get_all_files()
                for file in files:
                    fdt.update_data_file(file, len(fdt.get_array(file)))
                    x = fdt.file_downloaded(file)
                    if x == 1:
                        print(f"Downloaded {file}")
                    elif x == 0:
                        print(f"Not downloaded {file}")
                    else:
                        print(f"Downloading {file}")
            elif user_input.startswith("genmagnet "):
                parts = user_input.split()
                magnetGen(parts[1])
            elif user_input.startswith("usemagnet "):
                parts = user_input.split()
                sendMagenet(parts[1])
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
            threading.Thread(
                target=download, args=(torName, progress), daemon=True
            ).start()
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
#endregion

#region magnet
def magnetGen(torrent_file_name):
    torrent_file_name = f'program_{config.prog_num}/torrents/'+torrent_file_name
    print("magnet:?xt=urn:btih:"+trCtrl.get_torrent_hash(torrent_file_name).hex())
    
def extract_info_hash(magnet_link):
    """Extracts the info hash from a magnet link."""
    # Regular expression to find the info hash
    match = re.search(r'xt=urn:btih:([a-fA-F0-9]{40}|[a-fA-F0-9]{64})', magnet_link)
    if match:
        return bytes.fromhex(match.group(1)) # The info hash
    else:
        return None  # No valid info hash found

def sendMagenet(magnet):
    url = config.DEFAULT_TRACKER + "/announce/down"
    params = {}
    torrent_hash =  extract_info_hash(magnet)
    params["torrent_hash"] = torrent_hash
    params["peerid"] = config.peer_id
    port_list = trCom.send_get(url, params).json()
    for ip, c_port in port_list:
        c_port = int(c_port)
        if (c_port != int(port)):
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((ip, c_port))
            client.send(("Torrent file").encode())
            print(client.recv(1024).decode()) 
            client.send(torrent_hash)
            filename = client.recv(1024).decode()
            print(filename)
            filename = f"program_{config.prog_num}/torrents/" + filename
            client.settimeout(2)
            try:
                with open(filename, 'wb') as file:
                    while chunk := client.recv(1024):
                        # print(len(chunk))
                        file.write(chunk)
            except TimeoutError:
                print("Downloaded torrent file")
            client.close()
            return
#endregion

def main():
    help.welcome()  # Display the welcome message

    # Initialize Progress and Live objects
    show_progress = [False]
    progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        DownloadColumn(),
        TimeRemainingColumn(),
        console=console,
    )
    live = Live(progress, refresh_per_second=20, transient=True)
    upload_thread = Thread(target=upload)
    # destroy this upload thread on quitting
    upload_thread.daemon = True
    upload_thread.start()

    # Start the download manager in a background thread
    threading.Thread(target=download_manager, args=(progress,), daemon=True).start()
    # Start the input listener in a background thread
    threading.Thread(
        target=input_listener, args=(show_progress, live), daemon=True
    ).start()

    # Keep the main thread alive
    while running:
        if show_progress[0]:
            live.update(progress)  # Update live display when progress is shown
        time.sleep(1)


# Run the program
if __name__ == "__main__":
    port = 8000 + random.randint(0, 255)
    main()
