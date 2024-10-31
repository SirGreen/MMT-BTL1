import threading
from threading import Thread, Lock
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import json

# Define parameter
SERVER_PORT = 8080
SERVER_IP = "localhost"
RECEIVE_SIZE = 1024
CODE = "utf-8"


class Server:
    def __init__(self):
        # server_info
        self.port = SERVER_PORT
        self.ip = SERVER_IP

        # server_attributes
        self.active_client = []
        self.rfc_index = {}
        self.owner_file = {}
        self.lock = Lock()

    def client_join(self, peerid):
        # Thêm client vào danh sách active_client
        with self.lock:  # Bảo vệ truy cập đến active_client
            self.active_client.append(peerid)

        print(f"Welcome client: {peerid}")
        print(self.active_client)

    def down_find_peer(self, torrent_hash, port, peerid):
        # Initialize the list to store ports
        port_list = []
        # Check if the filename exists in rfc_index
        if torrent_hash in self.rfc_index:
            # For each client that has the file, add the port to port_list
            for client_info in self.rfc_index[torrent_hash]:
                port_list.append(client_info[1])  # Extract the port
        else:
            # If the file doesn't exist, port_list remains empty
            port_list = []
        print(port_list)
        return port_list

    def have_add_repo_client(self, port, torhash, peerid):
        # update rfc_index
        if torhash in self.rfc_index:
            self.rfc_index[torhash].append([peerid, port])
        else:
            self.rfc_index[torhash] = [[peerid, port]]

        # update owner_file
        if peerid in self.owner_file:
            self.owner_file[peerid].append(torhash)
        else:
            self.owner_file[peerid] = [torhash]
            
        print(self.rfc_index)
        print(self.owner_file)

    def new_client_connect(self, client_socket, addr):
        try:
            data = client_socket.recv(RECEIVE_SIZE).decode(CODE)
            print(f"Received data: {data}")
            data_list = data.split(" ")
            command = data_list[0]

            if command == "JOIN":
                # self.client_join(client_socket, data_list, addr)
                print("join called")
            elif command == "HAVE":
                if len(data_list) == 3:  # Kiểm tra số lượng tham số
                    self.have_add_repo_client(data_list, client_socket, addr)
                else:
                    print("Invalid HAVE command format.")
                    client_socket.send("Invalid HAVE command format.".encode(CODE))
            elif command == "DOWN":
                if len(data_list) == 2:  # Kiểm tra số lượng tham số
                    self.down_find_peer(data_list, client_socket)
                else:
                    print("Invalid DOWN command format.")
                    client_socket.send("Invalid DOWN command format.".encode(CODE))
            elif command == "EXIT":
                print("Client exit requested")
                self.client_exit(addr)
                return
        except ConnectionResetError:
            print("Connection reset by client")
        except Exception as e:
            print(f"Error occurred: {e}")
        finally:
            client_socket.close()

    # cmt
    def client_exit(self, peer_id):
        with self.lock:  # Sử dụng lock để bảo vệ truy cập
            self.active_client.remove(peer_id)
            if peer_id in self.owner_file:
                files_to_remove = self.owner_file[peer_id]

                for filename in files_to_remove:
                    if filename in self.rfc_index:
                        self.rfc_index[filename] = [
                            entry
                            for entry in self.rfc_index[filename]
                            if entry[0] != peer_id
                        ]
                        if not self.rfc_index[filename]:
                            del self.rfc_index[filename]

                del self.owner_file[peer_id]

                print(f"Client {peer_id} exited and files removed.")
            else:
                print(f"No files found for client {peer_id}.")
                
        print(self.rfc_index)
        print(self.owner_file)

    def handle_process(self, client_socket, addr):
        thread = Thread(target=self.new_client_connect, args=(client_socket, addr))
        # print("test handle")
        thread.daemon = True
        thread.start()


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
                    query_params.get("port", [None])[0],
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
                    query_params.get("port", [None])[0],
                    query_params.get("peerid", [None])[0],
                )
                response_data = json.dumps(peers)  # Convert list to JSON format

                self.send_header("Content-type", "application/json")  # Set content type to JSON
                self.end_headers()
                self.wfile.write(response_data.encode('utf-8'))
            elif path.startswith("/join"):
                self.send_response(200)
                parse_url = urlparse(path)
                query_params = parse_qs(parse_url.query)
                print(query_params)
                tracker_server.client_join(query_params.get("peerid", [None])[0])
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
        if command == 'shutdown':
            print("Shutting down server...")
            httpd.shutdown()
            server_thread.join()  # Wait for the server thread to finish
            print("Server has been shut down.")
            break
        if command.startswith("delete"):
            print(f'deleting {params[1]}')
            try:
                tracker_server.client_exit(params[1])
            except Exception as e:
                print(e)


if __name__ == "__main__":
    main()
