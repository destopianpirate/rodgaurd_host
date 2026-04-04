import requests
import random
import time

# IIT Gandhinagar Coordinates
# Lat: 23.2156, Lng: 72.6869
BASE_LAT = 23.2156
BASE_LNG = 72.6869

API_URL = "http://localhost:5000/api/potholes"

severity_levels = ["critical", "high", "medium", "low"]
labels = ["DEEP CRATER", "SHARP EDGE POTHOLE", "UNEVEN SURFACE", "RUTTING"]

for i in range(8):
    # Add small random offsets for cluster around IIT
    lat = BASE_LAT + random.uniform(-0.015, 0.015)
    lng = BASE_LNG + random.uniform(-0.015, 0.015)
    
    severity = random.choice(severity_levels)
    label = random.choice(labels)
    
    payload = {
        "lat": lat,
        "lng": lng,
        "severity": severity,
        "label": label
    }
    
    try:
        response = requests.post(API_URL, json=payload)
        if response.status_code == 201:
            print(f"Added pothole {i+1}: {lat:.4f}, {lng:.4f} ({severity})")
        else:
            print(f"Failed to add pothole {i+1}: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
        
    time.sleep(0.5)

print("Finished adding simulated potholes near IIT Gandhinagar.")
