import socket
import os
from threading import *
import random
import time
import tqdm

Flag = False
peer_repo = []
SERVER_PORT = 7775
SERVER_HOST = "localhost"
BLOCK = 128 << 10 # 128KB
BLOCK1 = 1 << 20 # 1024KB

def send_requests(msg : str, server_host, server_port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((server_host, server_port))
    client_socket.send(msg.encode())
    response = client_socket.recv(1024).decode()
    print(response)
    client_socket.close()
    return response

def peer_connect(client_socket):
    reponame = client_socket.recv(1024).decode()
    filename = ""
    for repo in peer_repo:
        if repo['reponame'] == reponame:
            filename = repo['filename']
    file_size = os.path.getsize(filename)
    #Print for another pear
    client_socket.send(("recievied_" + filename).encode())
    client_socket.send(str(file_size).encode())
    with (client_socket, client_socket.makefile('wb') as wfile):
        with open(filename, 'rb') as f1:
            while data := f1.read(BLOCK):
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
    while Flag != True:
        (client_socket,client_addr) = upload_socket.accept()
        print('Got connection from', client_addr)
        new_thread = Thread(target=peer_connect, args=(client_socket, ))
        new_thread.start()
    
    upload_socket.close()

def download(reponame):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    upload_host1 = socket.gethostbyname(socket.gethostname())
    msg = "FIND P2P-CI/1.0\nREPONAME:" + reponame
    send_requests(msg, "localhost", SERVER_PORT)
    #####
    port1 = int(input("Input peer port from list above: "))
    client.connect((upload_host1, port1))
    client.send(reponame.encode())
    file_name = client.recv(1024).decode()
    file_size = client.recv(1024).decode()
    print(file_name + " " + file_size)

    progress = tqdm.tqdm(unit='B', unit_scale=True, 
                         unit_divisor=1000, total=int(file_size))
    with client.makefile('rb') as rfile:
        with open(file_name, 'wb') as f:
            remaining = int(file_size)
            while remaining != 0:
                data = rfile.read(BLOCK1 if remaining > BLOCK1 else remaining)
                f.write(data)
                progress.update(len(data))
                remaining -= len(data)
        f.close()
    rfile.close()
    client.close()

def add(host):
    msg = "JOIN P2P-CI/1.0\nHost:"+host+'\n'+"Port:"+str(port)
    send_requests(msg, "localhost", SERVER_PORT)
    
def publish(host, title, filename):
    peer_repo.append({"filename" : title, "reponame" : filename})
    msg = "PUBLISH RFC P2P-CI/1.0\nHost:"+ host + '\n'+"Port:"+str(port)+'\n'+"File:"+ title + '\n'+ "Repo:"+ filename 
    send_requests(msg, "localhost", SERVER_PORT)


def command_line():
    hostname = input("Input your hostname: ")
    add(hostname)
    while True:
        command = input()
        command_split = command.split(' ')
        if command_split[0] == 'fetch':
            if len(command_split) != 2:
                print("Note : fetch only accept 1 argument")
            else:
                download(command_split[1])
        elif command_split[0] == 'publish':
            if len(command_split) != 3:
                print("Note : publish only accept 2 argument")
            else:
                publish(hostname, command_split[1], command_split[2])
        elif command_split[0] == 'find':
            if len(command_split) != 2:
                 print("Note : publish only accept 1 argument")
            else:
                find(command_split[1])
        elif command_split[0] == 'exit':
            exit(hostname)
            break
        elif command_split[0] == 'help':
            help()
        else:
            print('Command error!')


def main():
    upload_thread = Thread(target=upload)
    #destroy this upload thread on quitting
    upload_thread.daemon = True
    upload_thread.start()

    # ping_thread = Thread(target=recieve_ping)
    # ping_thread.daemon = True
    # ping_thread.start()

    command_line()

if __name__ == '__main__':
    port = 8000 + random.randint(0, 255)
    main()