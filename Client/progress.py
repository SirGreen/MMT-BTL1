import json
import config
import os

# The file where data will be stored
DATA_FILE = f'program_{config.prog_num}/downloads/'+"file_data.txt"

def update_data_file_dir():
    global DATA_FILE
    DATA_FILE = f'program_{config.prog_num}/downloads/'+"file_data.txt"
    
def update_data_file(file_name, n):
    if file_name not in get_all_files():
        if file_exists(file_name):
            add_file(file_name, [1] * n)
        else:
            add_file(file_name, [0] * n)
    
    if not file_exists(file_name):
        if file_name in get_all_files():
            update_array(file_name,[0]*n)

def file_downloaded(filename):
    array = get_array(filename)
    i = 0
    for _ in array:
        i = i + 1
    if i==len(array):
        return True
    else:
        return False

def file_exists(file_path):
    # Construct the full path
    full_path = f'program_{config.prog_num}/downloads/' + file_path
    
    # Check if the file exists
    return os.path.isfile(full_path)

# Function to load data from the text file
def load_data():
    try:
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        print("Create new file_data.txt")
        return {}
    except ValueError:
        print("File empty")
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
    print(f"File '{file_name}' added to file data.")

# Function to update the array for an existing file
def update_array(file_name, new_array):
    data = load_data()
    if file_name not in data:
        print(f"File '{file_name}' does not exist.")
        return
    data[file_name] = new_array
    save_data(data)
    print(f"File '{file_name}' updated with new array.")
    
def change_element(file_name, index, new_value):
    data = load_data()
    
    # Check if the file exists
    if file_name not in data:
        print(f"File '{file_name}' does not exist.")
        return

    # Check if the index is within bounds
    if index < 0 or index >= len(data[file_name]):
        print(f"Index {index} is out of bounds for the array in '{file_name}'.")
        return
    
    # Update the element in the array
    data[file_name][index] = new_value
    save_data(data)
    # print(f"Updated element at index {index} in '{file_name}' to {new_value}.")

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

