import threading
from threading import Lock
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import json

# Define parameter
SERVER_PORT = 8080
SERVER_IP = "localhost"
RECEIVE_SIZE = 1024
CODE = "utf-8"


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
        self.lock = Lock()

    def clean(self):
        self.active_client = {}
        self.rfc_index = {}
        self.owner_file = {}
        
        save_to_file(self.owner_file, "owner_file.dat")
        save_to_file(self.rfc_index, "rfc_index.dat")
        save_to_file(self.active_client, "active_client.dat")

    def client_join(self, peerid, port, ip):
        # Thêm client vào danh sách active_client
        with self.lock:  # Bảo vệ truy cập đến active_client
            self.active_client[peerid] = [ip, port]
        save_to_file(self.active_client, "active_client.dat")
        print(f"Welcome client: {peerid}")
        print(self.active_client)

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
        with self.lock:  # Sử dụng lock để bảo vệ truy cập
            self.active_client.pop(peer_id)
            if peer_id in self.owner_file:
                files_to_remove = self.owner_file[peer_id]
                for filename in files_to_remove:
                    if filename in self.rfc_index:
                        self.rfc_index[filename] = [
                            entry
                            for entry in self.rfc_index[filename]
                            if entry != peer_id
                        ]
                        if not self.rfc_index[filename]:
                            del self.rfc_index[filename]

                del self.owner_file[peer_id]

                print(f"Client {peer_id} exited and files removed.")
            else:
                print(f"No files found for client {peer_id}.")

        save_to_file(self.owner_file, "owner_file.dat")
        save_to_file(self.rfc_index, "rfc_index.dat")
        save_to_file(self.active_client, "active_client.dat")
        print(self.rfc_index)
        print(self.owner_file)


tracker_server = Server()


class Listener(BaseHTTPRequestHandler):
    try:

        def do_GET(self):
            if self.path.find("/announce") == -1:
                raise "Error URL"
            path = self.path[9:]
            print(path)
            if path == "/hello":
                self.send_response(200)
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Hello, World!")
            elif path.startswith("/have"):
                self.send_response(200)
                parse_url = urlparse(path)
                query_params = parse_qs(parse_url.query)
                tracker_server.have_add_repo_client(
                    query_params.get("torrent_hash", [None])[0],
                    query_params.get("peerid", [None])[0],
                )
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK!")
            elif path.startswith("/down"):
                self.send_response(200)
                parse_url = urlparse(path)
                query_params = parse_qs(parse_url.query)
                peers = tracker_server.down_find_peer(
                    query_params.get("torrent_hash", [None])[0],
                    query_params.get("peerid", [None])[0],
                )
                response_data = json.dumps(peers)  # Convert list to JSON format

                self.send_header(
                    "Content-type", "application/json"
                )  # Set content type to JSON
                self.end_headers()
                self.wfile.write(response_data.encode("utf-8"))
            elif path.startswith("/join"):
                self.send_response(200)
                parse_url = urlparse(path)
                query_params = parse_qs(parse_url.query)
                print(query_params)
                tracker_server.client_join(
                    query_params.get("peerid", [None])[0],
                    query_params.get("port", [None])[0],
                    self.client_address[0],
                )
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK!")
            elif path.startswith("/exit"):
                self.send_response(200)
                parse_url = urlparse(path)
                query_params = parse_qs(parse_url.query)
                print(query_params)
                tracker_server.client_exit(query_params.get("peerid", [None])[0])
                self.send_header("Content-type", "text/plain")
                self.end_headers()
                self.wfile.write(b"OK!")
            else:
                self.send_response(404)
                self.end_headers()
    except Exception as e:
        print(e)


def start_server():
    global httpd
    server_class = HTTPServer
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
