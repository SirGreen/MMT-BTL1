import requests
from config import DEFAULT_TRACKER

def send_get(url, params=None):
    try:
        # print(url)
        
        # Send the GET request
        response = requests.get(url, params=params)

        # Check if the request was successful
        response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)

        # Process the response
        # print("Response Status Code:", response.status_code)
        # print("Response Text:", response.text)  # or response.json() for JSON responses
        return response

    except requests.exceptions.HTTPError as http_err:
        print("HTTP error occurred:", http_err)
    except Exception as err:
        print("An error occurred:", err)

def send_tracker(cmd: str, params, tracker=None):
    if tracker is None:
        tracker = DEFAULT_TRACKER
    url = tracker+"/announce/"+cmd
    return send_get(url,params)