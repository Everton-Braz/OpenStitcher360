import requests
import os

# URL of the local server
url = "http://localhost:5000/stitch_custom"

data = {
    'fov': 200,
    'yaw_f': 0,
    'pitch_f': 0,
    'roll_f': 0,
    'shift_x_f': 0,
    'shift_y_f': 0,
    'mask_radius_f': 1400, # Test radius
    'yaw_b': 180,
    'pitch_b': 0,
    'roll_b': 0,
    'shift_x_b': 0,
    'shift_y_b': 0,
    'mask_radius_b': 1400,
    'threshold': 90,
    'erosion': 3
}

try:
    print("Sending request to", url)
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        print("Success!")
        print("Response:", response.json())
    else:
        print("Failed with status:", response.status_code)
        print("Response:", response.text)

except Exception as e:
    print("Error:", e)
