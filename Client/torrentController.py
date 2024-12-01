import os
import bencodepy
import hashlib
import config

DEFAULT_TRACKER = config.DEFAULT_TRACKER

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


def make_torrent(file_path, output_folder=None, tracker_url=DEFAULT_TRACKER, reFileName = False):
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

    # Bencode the data
    bencoded_data = bencodepy.encode(torrent_data)

    # Save to output folder or current directory
    torrent_name = f"{os.path.splitext(os.path.basename(file_path))[0]}.torrent"
    prog_num = config.prog_num
    output_path = os.path.join(output_folder if output_folder else f'program_{prog_num}/torrents', torrent_name)

    with open(output_path, "wb") as torrent_file:
        torrent_file.write(bencoded_data)

    print(f"Torrent file created: {output_path}")

    if reFileName:
        return torrent_name
    else:
        return output_path


def preview_torrent(torrent_file_path):
    """
    Parses and displays the contents of a .torrent file in a human-readable format.
    """
    torrent_file_path = f'program_{config.prog_num}/torrents/'+torrent_file_path
    
    if not os.path.exists(torrent_file_path):
        print(f"Error: The torrent file '{torrent_file_path}' does not exist.")
        return

    # Read and decode the torrent file
    try:
        with open(torrent_file_path, "rb") as f:
            torrent_data = bencodepy.decode(f.read())

        # Display the torrent contents in a readable format
        print("\n==== Torrent File Contents ====")
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

def get_trackers(torrent_file_path):
    """Extract and return tracker URLs from a torrent file."""
    try:
        # Open the torrent file and decode it
        with open(torrent_file_path, "rb") as file:
            torrent_data = bencodepy.decode(file.read())
        
        # Initialize an empty list to hold tracker URLs
        trackers = []
        
        # Extract the primary tracker URL if it exists
        if b'announce' in torrent_data:
            trackers.append(torrent_data[b'announce'].decode('utf-8'))
        
        # Extract additional trackers from the announce-list if they exist
        if b'announce-list' in torrent_data:
            for tier in torrent_data[b'announce-list']:
                for tracker in tier:
                    trackers.append(tracker.decode('utf-8'))

        return trackers

    except FileNotFoundError:
        print(f"Error: The file '{torrent_file_path}' was not found.")
        return []
    except ValueError:
        print(f"Error: Failed to decode '{torrent_file_path}' as a bencoded file.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return []

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

def get_file_name(torrent_file_path):
    """Extract and return the file name from a torrent file."""
    try:
        # Open the torrent file and decode it
        with open(torrent_file_path, "rb") as file:
            torrent_data = bencodepy.decode(file.read())
        
        # The file name is usually stored under 'info' > 'name'
        if b'info' in torrent_data and b'name' in torrent_data[b'info']:
            file_name = torrent_data[b'info'][b'name'].decode('utf-8')
            return file_name
        else:
            print("File name not found in torrent metadata.")
            return None

    except FileNotFoundError:
        print(f"Error: The file '{torrent_file_path}' was not found.")
        return None
    except ValueError:
        print(f"Error: Failed to decode '{torrent_file_path}' as a bencoded file.")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

def get_piece_length_from_torrent(torrent_file_name):
    with open(torrent_file_name, "rb") as file:
        # Decode the torrent file
        torrent_data = bencodepy.decode(file.read())
        
        # Extract file length from single or multiple files
        if b'info' in torrent_data:
            info = torrent_data[b'info']
            if b'piece length' in info:  # Single-file torrent
                return info[b'piece length']
        else:
            raise ValueError("Invalid torrent file: 'info' section missing")

def get_file_length(torrent_file_path):
    with open(torrent_file_path, "rb") as file:
        # Decode the torrent file
        torrent_data = bencodepy.decode(file.read())
        
        # Extract file length from single or multiple files
        if b'info' in torrent_data:
            info = torrent_data[b'info']
            if b'length' in info:  # Single-file torrent
                return info[b'length']
            elif b'files' in info:  # Multi-file torrent
                return sum(file[b'length'] for file in info[b'files'])
        else:
            raise ValueError("Invalid torrent file: 'info' section missing")