import requests
import os

# URL of the local server
url = "http://localhost:5000/stitch_custom"

# Test images (assuming they exist in uploads or images folder, or we can upload them)
# For this test, we'll assume the user has uploaded images or we use the test images logic in app.py
# If we don't provide files, app.py uses session or defaults to test images.
# We will try to trigger the default test images path by not sending files but sending parameters.

data = {
    'fov': 200,
    'yaw_f': 0,
    'pitch_f': 0,
    'roll_f': 0,
    'shift_x_f': 10,  # Test shift
    'shift_y_f': -10,
    'yaw_b': 180,
    'pitch_b': 0,
    'roll_b': 0,
    'shift_x_b': 5,
    'shift_y_b': 5,
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
