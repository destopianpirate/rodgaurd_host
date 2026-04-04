"""
Configuration for RoadGuard v2.0 — Collaborative Pothole Verification
Edit these values to match your hardware and server location.
"""

# ─── Vehicle Identity ────────────────────────────────────────
VEHICLE_ID = "car-001"               # Unique ID for this vehicle

# ─── Server Configuration ───────────────────────────────────
API_BASE_URL = "http://YOUR_SERVER_IP:5000/api"

# ─── Camera ──────────────────────────────────────────────────
CAMERA_RESOLUTION = (640, 480)
CAMERA_FRAMERATE = 30
CAPTURE_INTERVAL = 0.033             # Seconds — capture for 30 FPS

# ─── YOLOv8 Pothole Detection ───────────────────────────────
USE_CLOUD_API = False                 # Set to False to run local YOLO model (.pt file)
YOLO_MODEL_PATH = "best.pt"

# Cloud API configuration (used if USE_CLOUD_API is True)
ROBOFLOW_MODEL_ID = "pothole-detection-orxff/1"

POTHOLE_CONFIDENCE_THRESHOLD = 0.5
POTHOLE_CLASS_NAME = "pothole"

# ─── Thermal Camera (MLX90640) ───────────────────────────────
THERMAL_I2C_ADDRESS = 0x33
THERMAL_REFRESH_RATE = 2
ANIMAL_TEMP_MIN = 30.0
ANIMAL_TEMP_MAX = 42.0
ANIMAL_BLOB_MIN_PIXELS = 8
THERMAL_SCAN_INTERVAL = 2.0

# ─── GPS Module (NEO-6M) ────────────────────────────────────
GPS_SERIAL_PORT = "/dev/ttyS0"
GPS_BAUD_RATE = 9600
GPS_READ_INTERVAL = 1.0

# ─── Buzzer (GPIO) ──────────────────────────────────────────
BUZZER_GPIO_PIN = 18
BUZZER_PATTERN_POTHOLE = [(0.2, 0.1), (0.2, 0.1), (0.2, 0.5)]   # New pothole: triple beep
BUZZER_PATTERN_ANIMAL = [(0.5, 0.2), (0.5, 0.5)]                 # Animal: double long beep
BUZZER_PATTERN_VERIFIED = [(0.1, 0.1), (0.1, 0.3)]               # Verified: double short beep
BUZZER_COOLDOWN = 3.0                # Reduced for faster alerts while driving

# ─── Verification System ────────────────────────────────────
NEARBY_CHECK_RADIUS = 150            # Meters — fetch potholes within this radius
NEARBY_CHECK_INTERVAL = 5.0          # Seconds between server queries for nearby potholes

# ─── Severity Classification ────────────────────────────────
SEVERITY_THRESHOLDS = {
    "critical": 0.15,
    "high": 0.08,
    "medium": 0.03,
}

# ─── Logging ─────────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FILE = "roadguard.log"

# ─── Offline Queue ───────────────────────────────────────────
OFFLINE_QUEUE_FILE = "offline_queue.json"
MAX_QUEUE_SIZE = 1000
