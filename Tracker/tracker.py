import threading
from threading import Lock
import time
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import json


# Define parameter
SERVER_PORT = 8080
SERVER_IP = "localhost"
RECEIVE_SIZE = 1024
CODE = "utf-8"
MIN_TIMEOUT = 1800
CHECK_INTERVAL = 1800

def save_to_file(data, filename):
    """Save a list or dictionary to a file in JSON format."""
    with open(filename, "w") as file:
        json.dump(data, file)
    print(f"Data saved to {filename}")


def load_from_file(filename):
    """Load a list or dictionary from a JSON-formatted file."""
    if not os.path.exists(filename):
        # Create the file with an empty list as default data
        with open(filename, "w") as file:
            json.dump({}, file)
        print(f"{filename} did not exist and has been created with an empty list.")
        return {}

    with open(filename, "r") as file:
        data = json.load(file)
    print(f"Data loaded from {filename}")
    return data


class Server:
    def __init__(self):
        # server_info
        self.port = SERVER_PORT
        self.ip = SERVER_IP

        # server_attributes
        self.active_client = load_from_file("active_client.dat")
        self.rfc_index = load_from_file("rfc_index.dat")
        self.owner_file = load_from_file("owner_file.dat")
        self.last_activity = load_from_file("last_activity.dat")
        self.count_done_client = load_from_file("count_done_client.dat")
        self.lock = Lock()

        # Start the timeout checker thread
        self.timeout_checker_thread = threading.Thread(target=self.timeout_check, daemon=True)
        self.timeout_checker_thread.start()

    def timeout_check(self):
        timeout_event = threading.Event()
        while not timeout_event.wait(CHECK_INTERVAL):  # Chờ 30 phút
            try:
                current_time = time.time()
                cutoff_time = current_time - MIN_TIMEOUT

                with self.lock:
                    # Gather clients that are inactive and need to be removed
                    timeout_clients = [
                        peer_id for peer_id, last_time in self.last_activity.items() if last_time < cutoff_time
                    ]

                    # Xóa các client hết thời gian chờ
                for peer_id in timeout_clients:
                    print(f"Client {peer_id} timed out.")
                    self.client_exit(peer_id)

                    print(f"Client {peer_id} removed due to inactivity.")
            except Exception as e:
                print(f"Exception in timeout_check: {e}")

    def clean(self):
        self.active_client = {}
        self.rfc_index = {}
        self.owner_file = {}
        self.last_activity = {}
        self.count_done_client = {}
        
        save_to_file(self.owner_file, "owner_file.dat")
        save_to_file(self.rfc_index, "rfc_index.dat")
        save_to_file(self.active_client, "active_client.dat")
        save_to_file(self.last_activity, "last_activity.dat")
        save_to_file(self.count_done_client, "count_done_client.dat")

    def update_last_activity(self, peerid):
        with self.lock:
            self.last_activity[peerid] = time.time()
            save_to_file(self.last_activity, "last_activity.dat")
    
    def count_done_file(self, torrent_hash, peerid):
        # update done_file
        if torrent_hash in self.count_done_client:
            print(self.count_done_client[torrent_hash])
            print(peerid not in self.count_done_client[torrent_hash])
            if peerid not in self.count_done_client[torrent_hash]:
                self.count_done_client[torrent_hash].append(peerid)
        else:
            self.count_done_client[torrent_hash] = [peerid]
        
        save_to_file(self.count_done_client, "count_done_client.dat")
        self.have_add_repo_client(torrent_hash,peerid)

    def get_count_file(self, torrent_hash, file):
        if (file == "count_done_client.dat"):
            return len(self.count_done_client[torrent_hash])
        else: 
            return len(self.rfc_index[torrent_hash])

    def client_join(self, peerid, port, ip):
    # Thêm client vào danh sách active_client
        with self.lock:  # Bảo vệ truy cập đến active_client
            self.active_client[peerid] = [ip, port]
            self.last_activity[peerid] = time.time()  # Cập nhật thời gian hoạt động cuối cùng của client
        save_to_file(self.active_client, "active_client.dat")
        save_to_file(self.last_activity, "last_activity.dat")  # Lưu last_activity vào file
        print(f"Welcome client: {peerid}")
        print(self.active_client)


    def online_check(self, peerid):
    # Kiểm tra xem client có đang online không
        with self.lock:
            return peerid in self.active_client

    def down_find_peer(self, torrent_hash, peerid):
        # Initialize the list to store ports
        port_list = []
        # Check if the filename exists in rfc_index
        if torrent_hash in self.rfc_index:
            # For each client that has the file, add the port to port_list
            for client_info in self.rfc_index[torrent_hash]:
                port_list.append(self.active_client[client_info][1])  # Extract the port
        else:
            # If the file doesn't exist, port_list remains empty
            port_list = []
        print(port_list)
        self.have_add_repo_client(torrent_hash, peerid)
        return port_list

    def have_add_repo_client(self, torhash, peerid):
        # update rfc_index
        if torhash in self.rfc_index:
            print(self.rfc_index[torhash])
            print(peerid not in self.rfc_index[torhash])
            if peerid not in self.rfc_index[torhash]:
                self.rfc_index[torhash].append(peerid)
        else:
            self.rfc_index[torhash] = [peerid]

        # update owner_file
        if peerid in self.owner_file:
            self.owner_file[peerid].append(torhash)
        else:
            self.owner_file[peerid] = [torhash]
        save_to_file(self.owner_file, "owner_file.dat")
        save_to_file(self.rfc_index, "rfc_index.dat")
        print(self.rfc_index)
        print(self.owner_file)

    def client_exit(self, peer_id):
        with self.lock:  # Use lock to protect access to shared resources
            # Remove the client from active_client
            # print("ủa")
            self.active_client.pop(peer_id, None)

            # Remove files associated with the client in owner_file and rfc_index
            if peer_id in self.owner_file:
                files_to_remove = self.owner_file[peer_id]
                for filename in files_to_remove:
                    if filename in self.rfc_index:
                        # Remove the peer_id from the list of clients associated with each file
                        self.rfc_index[filename] = [
                            entry for entry in self.rfc_index[filename] if entry != peer_id
                        ]
                        # Delete the file entry if no clients are associated with it anymore
                        if not self.rfc_index[filename]:
                            del self.rfc_index[filename]

                # Delete the owner's file entries
                del self.owner_file[peer_id]
                print(f"Client {peer_id} exited and files removed.")
            else:
                print(f"No files found for client {peer_id}.")

            # Remove the client from last_activity
            # print("ở đây hong có gì")
            self.last_activity.pop(peer_id, None)

        # Save the updated data to files
        save_to_file(self.owner_file, "owner_file.dat")
        save_to_file(self.rfc_index, "rfc_index.dat")
        save_to_file(self.active_client, "active_client.dat")
        save_to_file(self.last_activity, "last_activity.dat")
        
        # For debugging: print the current state of the data structures
        print("Current rfc_index:", self.rfc_index)
        print("Current owner_file:", self.owner_file)
        print("Current last_activity:", self.last_activity)


tracker_server = Server()


class Listener(BaseHTTPRequestHandler):

    # Hàm tiện ích để gửi phản hồi HTTP
    def _send_response(self, code, content_type, message):
        self.send_response(code)
        self.send_header("Content-type", content_type)
        self.end_headers()
        self.wfile.write(message)

    def do_GET(self):
        try:
            # Verify URL starts with `/announce`
            if not self.path.startswith("/announce"):
                raise ValueError("Error: Invalid URL")

            # Parse path and query parameters
            path = self.path[9:]
            parse_url = urlparse(path)
            query_params = parse_qs(parse_url.query)
            peerid = query_params.get("peerid", [None])[0]

            # Simple `/hello` path - respond with "Hello, World!"
            if path == "/hello":
                self._send_response(200, "text/plain", b"Hello, World!")
                return

            # Handle `/join` - Check if client is joining
            elif path.startswith("/join"):
                if tracker_server.online_check(peerid):
                    self._send_response(409, "text/plain", b"Error: Client has already joined the system.")
                else:
                    port = query_params.get("port", [None])[0]
                    tracker_server.client_join(peerid, port, self.client_address[0])
                    self._send_response(200, "text/plain", b"OK!")
                tracker_server.update_last_activity(peerid)
                return

            # Check if the client is online for all other requests
            elif not tracker_server.online_check(peerid):
                self._send_response(403, "text/plain", b"Error: Client did not join the system.")
                return

            # Handle `/have` - Add client's torrent data
            elif path.startswith("/have"):
                torrent_hash = query_params.get("torrent_hash", [None])[0]
                tracker_server.have_add_repo_client(torrent_hash, peerid)
                self._send_response(200, "text/plain", b"OK!")
                tracker_server.update_last_activity(peerid)
                return
            
             # Handle `/done` - Update done status for a file
            elif path.startswith("/done"):
                torrent_hash = query_params.get("torrent_hash", [None])[0]
                tracker_server.count_done_file(torrent_hash, peerid)
                self._send_response(200, "text/plain", b"OK!")
                tracker_server.update_last_activity(peerid)
                return
            
            # Handle `/scrape` - Return seeder and leecher counts
            elif path.startswith("/scrape"):
                torrent_hash = query_params.get("torrent_hash", [None])[0]
                try:
                    seeder_count = tracker_server.get_count_file(torrent_hash, "count_done_client.dat")
                    leecher_count = tracker_server.get_count_file(torrent_hash, "rfc_index.dat")
                    response_message = f"Seeder: {seeder_count}, Leecher: {leecher_count}"
                    self._send_response(200, "text/plain", response_message.encode('utf-8'))
                except Exception as e:
                    print(f"Error occurred during /scrape: {e}")
                    self._send_response(500, "text/plain", b"Internal server error")
                tracker_server.update_last_activity(peerid)
                return

            # Handle `/down` - Find peers for a torrent
            elif path.startswith("/down"):
                torrent_hash = query_params.get("torrent_hash", [None])[0]
                peers = tracker_server.down_find_peer(torrent_hash, peerid)
                response_data = json.dumps(peers)
                self._send_response(200, "application/json", response_data.encode("utf-8"))
                tracker_server.update_last_activity(peerid)
                return

            # Handle `/ping` - Simple ping to check client status
            elif path.startswith("/ping"):
                self._send_response(200, "text/plain", b"OK!")
                tracker_server.update_last_activity(peerid)
                return

            # Handle `/exit` - Remove client from system
            elif path.startswith("/exit"):
                tracker_server.client_exit(peerid)
                self._send_response(200, "text/plain", b"OK!")
                return

            # Invalid path
            else:
                self._send_response(404, "text/plain", b"Error: Path not found.")

        except Exception as e:
            print(f"Exception occurred: {e}")
            self._send_response(500, "text/plain", b"Internal server error")
 



def start_server():
    global httpd
    server_class = ThreadingHTTPServer
    server_address = ("", SERVER_PORT)
    handler_class = Listener
    httpd = server_class(server_address, handler_class)
    print(f"Server on port: {SERVER_PORT}...")
    httpd.serve_forever()


server_thread = threading.Thread(target=start_server)
server_thread.start()


def main():
    # print('Server waiting for connections...')
    while True:
        command = input("Enter 'shutdown' to stop the server: ")
        command = command.strip()
        params = command.split()
        command = command.lower()
        if command == "shutdown":
            print("Shutting down server...")
            httpd.shutdown()
            # tracker_server.timeout_checker_thread.join()
            server_thread.join()  # Wait for the server thread to finish
            print("Server has been shut down.")
            break
        if command == "clean":
            print("Cleaning array...")
            tracker_server.clean()
        if command.startswith("delete"):
            print(f"deleting {params[1]}")
            try:
                tracker_server.client_exit(params[1])
            except Exception as e:
                print(e)


if __name__ == "__main__":
    main()