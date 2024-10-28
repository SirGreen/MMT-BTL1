import socket
from threading import Thread, Lock

# Define parameter 
SERVER_PORT = 8080
SERVER_IP = "localhost"
RECEIVE_SIZE = 1024
CODE = 'utf-8'

class Server:
    def __init__ (self):
        #server_info
        self.port = SERVER_PORT
        self.ip = SERVER_IP

        #server_connection
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip, self.port)) 
        self.server_socket.listen(5)
        print(f"Server listening on {self.ip}: {self.port}")

        #server_attributes
        self.active_client = []
        self.rfc_index = {}
        self.owner_file = {}
        self.lock = Lock()
    
    def client_join(self, client_socket, datalist, addr):
        ip, port = addr  # Lấy IP và port từ addr
        port = datalist[1]
        # Thêm client vào danh sách active_client
        with self.lock:  # Bảo vệ truy cập đến active_client
            self.active_client.append([ip, port])

        client_socket.send('Successfully joined the P2P network'.encode(CODE))
        print(f'Welcome client: {ip}, {port}')

   
    def down_find_peer(self, data_list, client_socket):
        # Extract the filename from the request
        filename = data_list[1]
        # Initialize the list to store ports
        port_list = []
        # Check if the filename exists in rfc_index
        if filename in self.rfc_index:
            #For each client that has the file, add the port to port_list
            for client_info in self.rfc_index[filename]:
                port_list.append(client_info[1])  # Extract the port
        else:
            # If the file doesn't exist, port_list remains empty
            port_list = []

        #   Join the ports with a newline separator
        response = "\n".join(map(str, port_list))
    
        # Send the response back to the client
        client_socket.send(response.encode(CODE))

    def have_add_repo_client(self, data_list, client_socket, addr):
        host, port = addr
        filename = data_list[2]
        port = data_list[1]
    
        # Chuyển ip_port thành tuple
        ip_port = (host, port)  
    
        # update rfc_index
        if filename in self.rfc_index:
            self.rfc_index[filename].append([host, port])
        else:
            self.rfc_index[filename] = [[host, port]]

        # update owner_file
        if ip_port in self.owner_file:
            self.owner_file[ip_port].append(filename)
        else:
            self.owner_file[ip_port] = [filename]

        response = "HAVE P2P-CI/1.0 200 OK"
        client_socket.send(response.encode(CODE))


    def new_client_connect(self, client_socket, addr):
        try:
            data = client_socket.recv(RECEIVE_SIZE).decode(CODE)
            print(f"Received data: {data}")
            data_list = data.split(' ')
            command = data_list[0]
        
            if command == 'JOIN':
                self.client_join(client_socket, data_list, addr)
            elif command == 'HAVE':
                if len(data_list) == 3:  # Kiểm tra số lượng tham số
                    self.have_add_repo_client(data_list, client_socket, addr)
                else:
                    print("Invalid HAVE command format.")
                    client_socket.send("Invalid HAVE command format.".encode(CODE))
            elif command == 'DOWN':
                if len(data_list) == 2:  # Kiểm tra số lượng tham số
                    self.down_find_peer(data_list, client_socket)
                else:
                    print("Invalid DOWN command format.")
                    client_socket.send("Invalid DOWN command format.".encode(CODE))
            elif command == 'EXIT':
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
    def client_exit(self, addr):
        ip, port = addr
        ip_port = (ip, port)  # Thay đổi từ list sang tuple

        with self.lock:  # Sử dụng lock để bảo vệ truy cập
            if ip_port in self.owner_file:
                files_to_remove = self.owner_file[ip_port]

                for filename in files_to_remove:
                    if filename in self.rfc_index:
                        self.rfc_index[filename] = [entry for entry in self.rfc_index[filename] if entry[0] != ip or entry[1] != port]
                        if not self.rfc_index[filename]:
                            del self.rfc_index[filename]

                del self.owner_file[ip_port]

                print(f"Client {ip}:{port} exited and files removed.")
            else:
                print(f"No files found for client {ip}:{port}.")

    def handle_process(self, client_socket, addr):
        thread = Thread(target=self.new_client_connect, args=(client_socket, addr))
        # print("test handle")
        thread.daemon = True
        thread.start()

def main():
    tracker_server = Server()
    print('Server waiting for connections...')
    try:
        while True:
            client_socket, addr = tracker_server.server_socket.accept()
            print(f"Connection established with {addr}")
            tracker_server.handle_process(client_socket, addr)
    finally:
        print('Shutting down server...')
        tracker_server.server_socket.close()

if __name__ == '__main__':
    main()
