Flag = False
peer_repo = []
SERVER_PORT = 8080
SERVER_HOST = "192.168.137.1"
DEFAULT_TRACKER = "http://" + SERVER_HOST + ":" + str(SERVER_PORT)
BLOCK_SZ = 512
BLOCK = 128 << 10  # 128KB
BLOCK1 = 1 << 20  # 1024KB
peer_id = "BKU-Torrent-" 
prog_num = 0
ping_time = 298 # 5min
offsetDownloader=0
# rows, cols = 5, 10
# downloadArray = [[0 for _ in range(cols)] for _ in range(rows)]

downloadArray = []
bytesDownload = []
timeStartDownload = []