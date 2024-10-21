import socket
from threading import Thread
import time
import sys
#Define parameter 
PORT = 7775

#Using array to store client 
active_client = []
rfc_index = []

def add_client(data_list, client_socket):
    host = data_list[1].split(':')[1]
    port = data_list[2].split(':')[1]
    active_client.append({"host" : host, "port" : port})
    client_socket.send('Sucessfully joined the P2P network'.encode())
    print(f'Welcome client : {host}')
    
def find_peer(data_list, client_socket):
    port_list = []
    filename = data_list[1].split(':')[1]
    # tmp_msg = f"\nList of clients that have file : {filename}\n"
    for rfc in rfc_index:
        if rfc['reponame'] == filename:
            # tmp_str = str(rfc['host']) + " " + str(rfc['port']) + '\n'
            # tmp_msg += tmp_str
            port_list.append(rfc['port'])
    
    port_string = '\n'.join(map(str, port_list))
    client_socket.send(port_string.encode())

def add_repo_client(data_list, client_socket):
    host = data_list[1].split(':')[1]
    filename = data_list[3].split(':')[1]
    port = data_list[2].split(':')[1]
    repo_name = data_list[4].split(':')[1]
    rfc_index.append({"host" : host, 
                      "port" : port, 
                      "filename" : filename, 
                      "reponame" : repo_name})
    response = "PUBLISH P2P-CI/1.0 200 OK"
    client_socket.send(response.encode())

def client_exit(data_list, client_socket):
    print(data_list)
    print(client_socket)

def new_client_connect(client_socket):
    data = client_socket.recv(1024).decode()
    data_list  = data.split('\n')
    if data_list[0].split(' ')[0] == 'JOIN':
        add_client(data_list,client_socket)
    elif data_list[0].split(' ')[0] == 'PUBLISH':
        add_repo_client(data_list,client_socket)
    elif data_list[0].split(' ')[0] == 'FIND':
        find_peer(data_list,client_socket)
    elif data_list[0].split(' ')[0] == 'EXIT':
        client_exit(data_list,client_socket)
        return

def handle_process(client_socket):
    thread1 = Thread(target=new_client_connect, args=(client_socket,))
    thread1.daemon = True
    thread1.start()

    # while True:
    #     command_line()


def main():
    #Initialize socket
    print('Server starting...')

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_host = socket.gethostbyname(socket.gethostname())
    server_socket.bind(('localhost', PORT))  
    # port : a placeholder for the actual port number 
    # where the server will be listening for incoming connections.
    
    # localhost: (or 127.0.0.1) is used here, 
    # meaning that this server will only accept connections from the local machine.

    server_socket.listen(5)
    #  start listening for incoming connection requests. handle up to 5 incoming connection requests at a time.
    print('Server waiting...')
    try:
        while True:
            client, addr = server_socket.accept()
            # The accept() method is used to accept an incoming connection request from a client. It returns two values:
            # client: A new socket object that represents the client connection.
            # addr: The address (IP address and port) of the client that just connected.
            thread = Thread(target=handle_process, args=(client,))
            thread.start()
    finally:
        #Shutdown
        print('Shut down server...')
        server_socket.close()


if __name__ == '__main__':
    main()