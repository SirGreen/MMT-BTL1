import random

Flag = False
peer_repo = []
SERVER_PORT = 8080
SERVER_HOST = "localhost"
DEFAULT_TRACKER = "http://" + SERVER_HOST + ":" + str(SERVER_PORT)
BLOCK_SZ = 512
BLOCK = 128 << 10  # 128KB
BLOCK1 = 1 << 20  # 1024KB
peer_id = "BKU-Torrent-" + "".join([str(random.randint(0, 9)) for _ in range(12)])