"""
Main Detection Loop — RoadGuard Raspberry Pi System v2.0
========================================================
Continuously runs camera + thermal detection with collaborative verification:
- Detects NEW potholes → buzzer fires → reports to server → shows on map
- Checks known potholes from server as car approaches
  - If camera still sees it → VERIFY (buzzer fires as warning)
  - If camera doesn't see it → RESOLVE (removed from map after consensus)
- Detects stray animals via thermal → buzzer fires → reports to server
"""

import time
import math
import signal
import sys
import logging
from datetime import datetime

# ─── Configuration ──────────────────────────────────────────
from config import (
    API_BASE_URL, VEHICLE_ID,
    CAMERA_RESOLUTION, CAPTURE_INTERVAL,
    YOLO_MODEL_PATH, POTHOLE_CONFIDENCE_THRESHOLD, SEVERITY_THRESHOLDS,
    ANIMAL_TEMP_MIN, ANIMAL_TEMP_MAX, ANIMAL_BLOB_MIN_PIXELS, THERMAL_REFRESH_RATE,
    THERMAL_SCAN_INTERVAL,
    GPS_SERIAL_PORT, GPS_BAUD_RATE,
    BUZZER_GPIO_PIN, BUZZER_COOLDOWN,
    BUZZER_PATTERN_POTHOLE, BUZZER_PATTERN_ANIMAL, BUZZER_PATTERN_VERIFIED,
    OFFLINE_QUEUE_FILE, MAX_QUEUE_SIZE,
    NEARBY_CHECK_RADIUS, NEARBY_CHECK_INTERVAL,
    LOG_LEVEL, LOG_FILE
)

from pothole_detector import PotholeDetector
from thermal_detector import ThermalDetector
from gps_reader import GPSReader
from buzzer import Buzzer
from api_client import APIClient

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# ─── Logging ────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode='a')
    ]
)
logger = logging.getLogger("RoadGuard")

running = True

def signal_handler(sig, frame):
    global running
    logger.info("Shutdown signal received...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def haversine_distance(lat1, lon1, lat2, lon2):
    """Distance in meters between two GPS points."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


class RoadGuardSystem:
    """Main system with collaborative pothole verification."""

    def __init__(self):
        logger.info("=" * 60)
        logger.info("  RoadGuard v2.0 — Collaborative Pothole Verification")
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

        # Timing
        self.last_capture_time = 0
        self.last_thermal_time = 0
        self.last_nearby_check_time = 0

        # Cache of known nearby potholes from the server
        self.known_potholes = []

        # Track recently verified/resolved to avoid repeats
        self.recently_handled = {}  # pothole_id -> timestamp

        # Stats
        self.stats = {"new_potholes": 0, "verified": 0, "resolved": 0, "animals": 0}

        self._print_status()

    # ─── Initialization ─────────────────────────────────────

    def _init_camera(self):
        if CV2_AVAILABLE:
            try:
                self.camera = cv2.VideoCapture(0)
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_RESOLUTION[0])
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_RESOLUTION[1])
                if self.camera.isOpened():
                    logger.info(f"📷 Camera: ✅ ({CAMERA_RESOLUTION[0]}x{CAMERA_RESOLUTION[1]})")
                else:
                    logger.error("📷 Camera: ❌ Failed to open")
                    self.camera = None
            except Exception as e:
                logger.error(f"Camera error: {e}")
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
        self.gps = GPSReader(port=GPS_SERIAL_PORT, baud_rate=GPS_BAUD_RATE)
        connected = self.gps.connect()
        logger.info(f"📍 GPS: {'✅' if connected else '⚠️ Not connected'}")

    def _init_buzzer(self):
        self.buzzer = Buzzer(pin=BUZZER_GPIO_PIN, cooldown=BUZZER_COOLDOWN)
        logger.info("🔔 Buzzer: ✅")

    def _init_api_client(self):
        self.api_client = APIClient(
            base_url=API_BASE_URL, vehicle_id=VEHICLE_ID,
            offline_queue_file=OFFLINE_QUEUE_FILE, max_queue_size=MAX_QUEUE_SIZE
        )
        ok = self.api_client.health_check()
        logger.info(f"🌐 Server: {'✅ Connected' if ok else '⚠️ Offline'}")

    def _print_status(self):
        logger.info("-" * 60)
        logger.info(f"  Nearby check radius: {NEARBY_CHECK_RADIUS}m")
        logger.info(f"  Nearby check interval: {NEARBY_CHECK_INTERVAL}s")
        logger.info(f"  Capture interval: {CAPTURE_INTERVAL}s")
        logger.info("-" * 60)
        logger.info("🚗 Driving... Press Ctrl+C to stop.\n")

    # ─── Main Loop ──────────────────────────────────────────

    def run(self):
        global running

        while running:
            try:
                now = time.time()

                # 1. Read GPS
                gps_data = self.gps.read() if self.gps else None

                # 2. Periodically fetch known potholes from server
                if now - self.last_nearby_check_time >= NEARBY_CHECK_INTERVAL:
                    self.last_nearby_check_time = now
                    self._fetch_nearby_potholes(gps_data)

                # 3. Capture frame and run pothole detection
                if now - self.last_capture_time >= CAPTURE_INTERVAL:
                    self.last_capture_time = now
                    self._process_frame(gps_data)

                # 4. Thermal animal detection
                if now - self.last_thermal_time >= THERMAL_SCAN_INTERVAL:
                    self.last_thermal_time = now
                    self._detect_animals(gps_data)

                time.sleep(0.01)

            except Exception as e:
                logger.error(f"Loop error: {e}", exc_info=True)
                time.sleep(1)

        self._shutdown()

    # ─── Fetch Known Potholes ───────────────────────────────

    def _fetch_nearby_potholes(self, gps_data):
        """Fetch known active potholes near our current position from the server."""
        if not gps_data or not self.api_client:
            return

        self.known_potholes = self.api_client.get_nearby_potholes(
            gps_data["lat"], gps_data["lng"], radius=NEARBY_CHECK_RADIUS
        )

        if self.known_potholes:
            logger.debug(f"📡 {len(self.known_potholes)} known pothole(s) nearby")

    # ─── Process Frame: Detect + Verify/Resolve ─────────────

    def _process_frame(self, gps_data):
        """
        Core logic:
        1. Capture camera frame
        2. Run YOLO pothole detection
        3. If pothole detected:
           - Check if it matches a known pothole → VERIFY it (buzzer warns)
           - If no match → report as NEW pothole (buzzer alerts)
        4. If NO pothole detected but we're near a known pothole:
           - RESOLVE it (pothole seems fixed)
        """
        if not self.camera or not self.pothole_detector:
            return

        ret, frame = self.camera.read()
        if not ret or frame is None:
            return

        lat = gps_data["lat"] if gps_data else 0.0
        lng = gps_data["lng"] if gps_data else 0.0

        # Run YOLO detection
        detections = self.pothole_detector.detect(frame)
        detected_something = len(detections) > 0

        if detected_something:
            for det in detections:
                severity = det["severity"]
                confidence = det["confidence"]

                # Check if this matches a known pothole
                matched_pothole = self._find_matching_known(lat, lng)

                if matched_pothole:
                    # ── VERIFY: pothole still exists ──────────
                    pid = matched_pothole["id"]
                    if not self._recently_handled(pid):
                        self.api_client.verify_pothole(pid)
                        self.buzzer.alert_pothole(BUZZER_PATTERN_VERIFIED)
                        self.recently_handled[pid] = time.time()
                        self.stats["verified"] += 1
                        logger.info(f"✅ VERIFIED pothole #{pid} at ({lat:.5f}, {lng:.5f})")
                else:
                    # ── NEW POTHOLE ───────────────────────────
                    result = self.api_client.send_pothole(
                        lat=lat, lng=lng, severity=severity, confidence=confidence,
                        description=f"Auto-detected ({det.get('class_name', 'pothole')})"
                    )
                    self.buzzer.alert_pothole(BUZZER_PATTERN_POTHOLE)
                    self.stats["new_potholes"] += 1
                    action = result.get("action", "reported") if result else "queued"
                    logger.info(f"🕳️  NEW POTHOLE [{action}] severity={severity} "
                               f"conf={confidence:.0%} at ({lat:.5f}, {lng:.5f})")
        else:
            # No pothole detected — check if we're passing a known one
            self._check_absent_potholes(lat, lng)

    def _find_matching_known(self, lat, lng, max_dist=30):
        """Check if current position is near any known pothole."""
        for kp in self.known_potholes:
            dist = haversine_distance(lat, lng, kp["lat"], kp["lng"])
            if dist < max_dist:
                return kp
        return None

    def _check_absent_potholes(self, lat, lng):
        """
        If we're very close to a known pothole but camera doesn't see one,
        it might be fixed. Report it as potentially resolved.
        """
        for kp in self.known_potholes:
            dist = haversine_distance(lat, lng, kp["lat"], kp["lng"])
            # Only resolve if we're really close (within 15m) and we haven't recently handled
            if dist < 15 and not self._recently_handled(kp["id"]):
                self.api_client.resolve_pothole(kp["id"])
                self.recently_handled[kp["id"]] = time.time()
                self.stats["resolved"] += 1
                logger.info(f"🔧 ABSENT: pothole #{kp['id']} not detected at ({lat:.5f}, {lng:.5f}) "
                           f"— reported for resolution")

    def _recently_handled(self, pothole_id, cooldown=60):
        """Check if we already verified/resolved this pothole recently."""
        last = self.recently_handled.get(pothole_id)
        if last and (time.time() - last) < cooldown:
            return True
        return False

    # ─── Animal Detection ───────────────────────────────────

    def _detect_animals(self, gps_data):
        if not self.thermal_detector:
            return

        detections = self.thermal_detector.scan()
        if not detections:
            return

        lat = gps_data["lat"] if gps_data else 0.0
        lng = gps_data["lng"] if gps_data else 0.0

        for det in detections:
            self.stats["animals"] += 1
            logger.info(f"🐾 ANIMAL: {det['animal_type']} temp={det['avg_temperature']}°C "
                       f"at ({lat:.5f}, {lng:.5f})")

            self.buzzer.alert_animal(BUZZER_PATTERN_ANIMAL)
            self.api_client.send_animal(
                lat=lat, lng=lng,
                animal_type=det["animal_type"],
                temperature=det["avg_temperature"],
                confidence=det["confidence"],
                description=f"Thermal ({det['warm_pixel_count']} warm pixels)"
            )

    # ─── Shutdown ───────────────────────────────────────────

    def _shutdown(self):
        logger.info("\n🛑 Shutting down RoadGuard...")
        if self.camera:
            self.camera.release()
        if self.gps:
            self.gps.disconnect()
        if self.buzzer:
            self.buzzer.cleanup()

        logger.info(f"\n📊 Session Summary:")
        logger.info(f"  New potholes reported: {self.stats['new_potholes']}")
        logger.info(f"  Potholes verified:     {self.stats['verified']}")
        logger.info(f"  Potholes resolved:     {self.stats['resolved']}")
        logger.info(f"  Animals detected:      {self.stats['animals']}")
        logger.info(f"  Offline queue:         {self.api_client.get_queue_size()} pending")
        logger.info("Goodbye! 👋\n")


if __name__ == "__main__":
    system = RoadGuardSystem()
    system.run()
