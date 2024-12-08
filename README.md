# MMT-BTL1
Bittorrentを発展する。

# How to Use

Follow these steps to set up and use the program for file transfer.

## Prerequisites
- Ensure all devices are connected to the same Local Area Network (LAN).

## Steps

### 1. Start the Tracker
Run `tracker.py` on the machine that will act as the tracker.

### 2. Start the Client
Run `client.py` on both the **seeder** and **leacher** machines.

---

### 3. Seeder Instructions
1. **Prepare the File:**
   - Place the file you want to transfer in the `program_{id}/downloads` folder.

2. **Create a Torrent File:**
   - Use the command:  
     ```bash
     maketor <filename>
     ```
     This will generate a torrent file for the specified file.

3. **Register the Torrent with the Tracker:**
   - Use the command:  
     ```bash
     have <torrent_file_name>
     ```
     This registers the torrent file with the tracker.

---

### 4. Leacher Instructions
1. **Obtain the Torrent File:**
   - Transfer the torrent file from the seeder to the leacher (e.g., via email, USB, or file sharing). Torrent files are lightweight and easy to share.

2. **Start the Download:**
   - Use the command:  
     ```bash
     down <torrent_file_name>
     ```

3. **Check Download Progress:**
   - Use the command:  
     ```bash
     progress
     ```

4. **Access the Downloaded File:**
   - Once the download is complete, the file will be available in the `program_{id}/downloads` folder.

---

By following these steps, you can successfully transfer files between devices on the same LAN.

Use help to view more commands
