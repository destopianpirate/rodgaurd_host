"""
Main Detection Loop — RoadGuard Laptop Migration
Continuously runs webcam + thermal simulation with collaborative verification.
"""

import time
import math
import signal
import sys
import logging
import os

# Add raspberry_pi directory to path to reuse shared component models
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'raspberry_pi')))

# ─── Configuration ───
from config import (
    API_BASE_URL, VEHICLE_ID,
    CAMERA_RESOLUTION, CAPTURE_INTERVAL,
    YOLO_MODEL_PATH, POTHOLE_CONFIDENCE_THRESHOLD, SEVERITY_THRESHOLDS,
    ANIMAL_TEMP_MIN, ANIMAL_TEMP_MAX, ANIMAL_BLOB_MIN_PIXELS, THERMAL_REFRESH_RATE,
    THERMAL_SCAN_INTERVAL,
    BUZZER_COOLDOWN,
    BUZZER_PATTERN_POTHOLE, BUZZER_PATTERN_ANIMAL, BUZZER_PATTERN_VERIFIED,
    OFFLINE_QUEUE_FILE, MAX_QUEUE_SIZE,
    NEARBY_CHECK_RADIUS, NEARBY_CHECK_INTERVAL,
    LOG_LEVEL, LOG_FILE
)

from pothole_detector import PotholeDetector
from thermal_detector import ThermalDetector
from api_client import APIClient

# Use laptop specific buzzer and GPS
from gps_reader import GPSReader
from buzzer import Buzzer

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')
    ]
)
logger = logging.getLogger("RoadGuardLaptop")

running = True

def signal_handler(sig, frame):
    global running
    logger.info("Shutdown signal received...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class RoadGuardLaptop:

    def __init__(self):
        logger.info("=" * 60)
        logger.info("  RoadGuard Laptop Setup — Collaborative Verification")
        logger.info(f"  Vehicle ID: {VEHICLE_ID}")
        logger.info("=" * 60)

        self.camera = None
        self.pothole_detector = None
        self.thermal_detector = None
        self.gps = None
        self.buzzer = None
        self.api_client = None

        self._init_camera()
        self._init_pothole_detector()
        self._init_thermal_detector()
        self._init_gps()
        self._init_buzzer()
        self._init_api_client()

        self.last_capture_time = 0
        self.last_thermal_time = 0
        self.last_nearby_check_time = 0
        self.known_potholes = []
        self.recently_handled = {}
        self.stats = {"new_potholes": 0, "verified": 0, "resolved": 0, "animals": 0}
        self.last_detection_time = 0

        self._print_status()

    def _init_camera(self):
        if CV2_AVAILABLE:
            try:
                self.camera = cv2.VideoCapture(0)
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_RESOLUTION[0])
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_RESOLUTION[1])
                if self.camera.isOpened():
                    logger.info(f"📷 WebCam: ✅ ({CAMERA_RESOLUTION[0]}x{CAMERA_RESOLUTION[1]})")
                else:
                    logger.error("📷 WebCam: ❌ Failed to open")
                    self.camera = None
            except Exception as e:
                logger.error(f"WebCam error: {e}")
                self.camera = None
        else:
            logger.warning("📷 Camera: ❌ OpenCV not available")

    def _init_pothole_detector(self):
        self.pothole_detector = PotholeDetector(
            model_path=YOLO_MODEL_PATH,
            confidence_threshold=POTHOLE_CONFIDENCE_THRESHOLD,
            severity_thresholds=SEVERITY_THRESHOLDS
        )
        logger.info(f"🕳️  Detector: {'✅' if self.pothole_detector.is_ready() else '❌'}")

    def _init_thermal_detector(self):
        self.thermal_detector = ThermalDetector(
            temp_min=ANIMAL_TEMP_MIN, temp_max=ANIMAL_TEMP_MAX,
            min_blob_pixels=ANIMAL_BLOB_MIN_PIXELS, refresh_rate=THERMAL_REFRESH_RATE
        )
        logger.info(f"🌡️  Thermal: {'✅' if self.thermal_detector.is_ready() else '⚠️ Sim mode'}")

    def _init_gps(self):
        self.gps = GPSReader()
        connected = self.gps.connect()
        logger.info(f"📍 GPS (IP Geolocation): {'✅' if connected else '⚠️ Not connected'}")

    def _init_buzzer(self):
        self.buzzer = Buzzer(cooldown=BUZZER_COOLDOWN)

    def _init_api_client(self):
        self.api_client = APIClient(
            base_url=API_BASE_URL, vehicle_id=VEHICLE_ID,
            offline_queue_file=OFFLINE_QUEUE_FILE, max_queue_size=MAX_QUEUE_SIZE
        )
        ok = self.api_client.health_check()
        logger.info(f"🌐 Server: {'✅ Connected' if ok else '⚠️ Offline (Will Queue)'}")

    def _print_status(self):
        logger.info("-" * 60)
        logger.info("💻 Running on Laptop. Press Ctrl+C to stop.\n")

    def run(self):
        global running
        while running:
            try:
                now = time.time()
                gps_data = self.gps.read() if self.gps else None

                if now - self.last_nearby_check_time >= NEARBY_CHECK_INTERVAL:
                    self.last_nearby_check_time = now
                    self._fetch_nearby_potholes(gps_data)

                if now - self.last_capture_time >= CAPTURE_INTERVAL:
                    self.last_capture_time = now
                    self._process_frame(gps_data)

                if now - self.last_thermal_time >= THERMAL_SCAN_INTERVAL:
                    self.last_thermal_time = now
                    self._detect_animals(gps_data)

                time.sleep(0.01)

            except Exception as e:
                logger.error(f"Loop error: {e}", exc_info=True)
                time.sleep(1)

        self._shutdown()

    def _fetch_nearby_potholes(self, gps_data):
        if not gps_data or not self.api_client: return
        self.known_potholes = self.api_client.get_nearby_potholes(gps_data["lat"], gps_data["lng"], radius=NEARBY_CHECK_RADIUS)

    def _process_frame(self, gps_data):
        if not self.camera or not self.pothole_detector: return

        ret, frame = self.camera.read()
        if not ret or frame is None: return

        if time.time() - self.last_detection_time < 2.0:
            if CV2_AVAILABLE:
                cv2.imshow("RoadGuard Detection", frame)
                cv2.waitKey(1)
            return

        lat = gps_data["lat"] if gps_data else 0.0
        lng = gps_data["lng"] if gps_data else 0.0

        detections = self.pothole_detector.detect(frame)

        if CV2_AVAILABLE:
            annotated = self.pothole_detector.draw_detections(frame, detections)
            cv2.imshow("RoadGuard Detection", annotated)
            cv2.waitKey(1)

        if detections:
            for det in detections:
                severity = det["severity"]
                confidence = det["confidence"]
                matched = self._find_matching_known(lat, lng)

                if matched:
                    pid = matched["id"]
                    if not self._recently_handled(pid):
                        self.api_client.verify_pothole(pid)
                        self.buzzer.alert_verified(BUZZER_PATTERN_VERIFIED)
                        self.recently_handled[pid] = time.time()
                        self.stats["verified"] += 1
                        logger.info(f"✅ VERIFIED pothole #{pid}")
                else:
                    result = self.api_client.send_pothole(
                        lat=lat, lng=lng, severity=severity, confidence=confidence,
                        description=f"Laptop auto-detected ({det.get('class_name', 'pothole')})"
                    )
                    self.buzzer.alert_pothole(BUZZER_PATTERN_POTHOLE)
                    self.stats["new_potholes"] += 1
                    logger.info(f"🕳️ NEW POTHOLE severity={severity} conf={confidence:.0%}")
            
            self.last_detection_time = time.time()
        else:
            self._check_absent_potholes(lat, lng)

    def _find_matching_known(self, lat, lng, max_dist=30):
        for kp in self.known_potholes:
            if haversine_distance(lat, lng, kp["lat"], kp["lng"]) < max_dist:
                return kp
        return None

    def _check_absent_potholes(self, lat, lng):
        for kp in self.known_potholes:
            if haversine_distance(lat, lng, kp["lat"], kp["lng"]) < 15 and not self._recently_handled(kp["id"]):
                self.api_client.resolve_pothole(kp["id"])
                self.recently_handled[kp["id"]] = time.time()
                self.stats["resolved"] += 1
                logger.info(f"🔧 ABSENT: pothole #{kp['id']} not detected — resolving")

    def _recently_handled(self, pothole_id, cooldown=60):
        last = self.recently_handled.get(pothole_id)
        return bool(last and (time.time() - last) < cooldown)

    def _detect_animals(self, gps_data):
        if not self.thermal_detector: return
        detections = self.thermal_detector.scan()
        if not detections: return

        lat = gps_data["lat"] if gps_data else 0.0
        lng = gps_data["lng"] if gps_data else 0.0

        for det in detections:
            self.stats["animals"] += 1
            self.buzzer.alert_animal(BUZZER_PATTERN_ANIMAL)
            self.api_client.send_animal(
                lat=lat, lng=lng, animal_type=det["animal_type"],
                temperature=det["avg_temperature"], confidence=det["confidence"],
                description="Thermal Simulation"
            )

    def _shutdown(self):
        logger.info("\n🛑 Shutting down RoadGuard Laptop...")
        if self.camera: self.camera.release()
        if CV2_AVAILABLE: cv2.destroyAllWindows()
        if self.gps: self.gps.disconnect()
        if self.buzzer: self.buzzer.cleanup()
        logger.info("Goodbye! 👋\n")

if __name__ == "__main__":
    app = RoadGuardLaptop()
    app.run()
