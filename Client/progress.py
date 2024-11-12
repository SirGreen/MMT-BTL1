import json
import config

# The file where data will be stored
DATA_FILE = f'program_{config.prog_num}/downloads/'+"file_data.txt"

def update_data_file():
    global DATA_FILE
    DATA_FILE = f'program_{config.prog_num}/downloads/'+"file_data.txt"


# Function to load data from the text file
def load_data():
    try:
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# Function to save data to the text file
def save_data(data):
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file)

# Function to add a new file with a boolean array
def add_file(file_name, bool_array):
    data = load_data()
    if file_name in data:
        print(f"File '{file_name}' already exists.")
        return
    data[file_name] = bool_array
    save_data(data)
    print(f"File '{file_name}' added with array {bool_array}.")

# Function to update the array for an existing file
def update_array(file_name, new_array):
    data = load_data()
    if file_name not in data:
        print(f"File '{file_name}' does not exist.")
        return
    data[file_name] = new_array
    save_data(data)
    print(f"File '{file_name}' updated with new array {new_array}.")

# Function to get a list of all files
def get_all_files():
    data = load_data()
    return list(data.keys())

# Function to get the array associated with a specific file name
def get_array(file_name):
    data = load_data()
    if file_name in data:
        return data[file_name]
    else:
        print(f"File '{file_name}' does not exist.")
        return None

