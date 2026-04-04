"""
Configuration for RoadGuard v2.0 — Laptop Migration
Edit these values to match your localhost environment.
"""

import os

# ─── Vehicle Identity ────────────────────────────────────────
VEHICLE_ID = "laptop-001"           

# ─── Server Configuration ───────────────────────────────────
API_BASE_URL = "http://127.0.0.1:5000/api"

# ─── Camera ──────────────────────────────────────────────────
CAMERA_RESOLUTION = (640, 480)
CAMERA_FRAMERATE = 30
CAPTURE_INTERVAL = 0.033             

# ─── YOLOv8 Pothole Detection ───────────────────────────────
USE_CLOUD_API = False                
YOLO_MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "runs", "detect", "pothole_blur_augmented2", "weights", "best.pt"))

POTHOLE_CONFIDENCE_THRESHOLD = 0.5
POTHOLE_CLASS_NAME = "pothole"

# ─── Thermal Camera (MLX90640 - Will run in Simulation) ──────
THERMAL_REFRESH_RATE = 2
ANIMAL_TEMP_MIN = 30.0
ANIMAL_TEMP_MAX = 42.0
ANIMAL_BLOB_MIN_PIXELS = 8
THERMAL_SCAN_INTERVAL = 2.0

# ─── GPS Module (IP Geolocation Fallback) ───────────────────
# We use IP geolocation instead of Serial port
GPS_READ_INTERVAL = 1.0

# ─── Buzzer (Windows winsound) ──────────────────────────────
BUZZER_PATTERN_POTHOLE = [(0.2, 0.1), (0.2, 0.1), (0.2, 0.5)]   # New pothole: triple beep
BUZZER_PATTERN_ANIMAL = [(0.5, 0.2), (0.5, 0.5)]                 # Animal: double long beep
BUZZER_PATTERN_VERIFIED = [(0.1, 0.1), (0.1, 0.3)]               # Verified: double short beep
BUZZER_COOLDOWN = 3.0                

# ─── Verification System ────────────────────────────────────
NEARBY_CHECK_RADIUS = 150            
NEARBY_CHECK_INTERVAL = 5.0          

# ─── Severity Classification ────────────────────────────────
SEVERITY_THRESHOLDS = {
    "critical": 0.15,
    "high": 0.08,
    "medium": 0.03,
}

# ─── Logging ─────────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FILE = "roadguard_laptop.log"

# ─── Offline Queue ───────────────────────────────────────────
OFFLINE_QUEUE_FILE = "offline_queue_laptop.json"
MAX_QUEUE_SIZE = 1000
