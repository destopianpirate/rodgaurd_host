"""
RoadGuard v2.1 — Smooth Real-Time Detection
=============================================
3-Thread Architecture:
  - Main Thread  : Camera capture + display (smooth ~30 FPS)
  - YOLO Thread  : Detection with 2-second cooldown
  - GPS Thread   : Continuous background GPS reading
"""

import time
import sys
import signal
import logging
import threading
import cv2
import numpy as np

# ─── Configuration ──────────────────────────────────────────
from config import (
    API_BASE_URL, VEHICLE_ID,
    CAMERA_RESOLUTION, YOLO_MODEL_PATH,
    POTHOLE_CONFIDENCE_THRESHOLD, SEVERITY_THRESHOLDS,
    GPS_SERIAL_PORT, GPS_BAUD_RATE,
    BUZZER_GPIO_PIN, BUZZER_COOLDOWN,
    BUZZER_PATTERN_POTHOLE, BUZZER_PATTERN_VERIFIED,
    OFFLINE_QUEUE_FILE, MAX_QUEUE_SIZE,
    LOG_LEVEL, LOG_FILE
)

from pothole_detector import PotholeDetector
from gps_reader import GPSReader
from buzzer import Buzzer
from api_client import APIClient

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("RoadGuard")

# ─── Window name constant ──────────────────────────────────
WINDOW_NAME = "RoadGuard Real-Time"


class RoadGuardSystem:
    def __init__(self):
        self.picam2 = None
        self.pothole_detector = None
        self.gps = None
        self.buzzer = None
        self.api_client = None

        # Shared state (thread-safe via GIL for simple reads/writes)
        self.latest_frame = None
        self.latest_detections = []
        self.last_report_time = 0
        self.report_cooldown = 2.0  # seconds between detections

        self.stats = {"new_potholes": 0, "verified": 0, "resolved": 0}

        # Shutdown event — all threads check this
        self.shutdown_event = threading.Event()

        self._init_hardware()

    def _init_hardware(self):
        """Initialize all hardware with safe fallbacks."""

        # 1. Camera (Picamera2)
        try:
            from picamera2 import Picamera2
            self.picam2 = Picamera2()
            config = self.picam2.create_preview_configuration(
                main={"format": "RGB888", "size": (640, 480)}
            )
            self.picam2.configure(config)
            self.picam2.start()
            time.sleep(0.5)  # let camera warm up
            logger.info("Camera: OK")
        except Exception as e:
            logger.error(f"Camera: FAILED — {e}")
            self.picam2 = None

        # 2. YOLO Detector
        try:
            self.pothole_detector = PotholeDetector(
                YOLO_MODEL_PATH, POTHOLE_CONFIDENCE_THRESHOLD
            )
            logger.info("YOLO Detector: OK")
        except Exception as e:
            logger.error(f"YOLO Detector: FAILED — {e}")

        # 3. GPS (background thread reader)
        try:
            self.gps = GPSReader(GPS_SERIAL_PORT, GPS_BAUD_RATE)
            self.gps.connect()
            logger.info("GPS: OK")
        except Exception as e:
            logger.warning(f"GPS: FAILED — {e}")
            self.gps = None

        # 4. Buzzer — ensure OFF at init
        try:
            self.buzzer = Buzzer(BUZZER_GPIO_PIN, BUZZER_COOLDOWN)
            self.buzzer.force_off()  # guarantee silence at startup
            logger.info("Buzzer: OK (forced OFF)")
        except Exception as e:
            logger.warning(f"Buzzer: FAILED — {e}")
            self.buzzer = None

        # 5. API Client
        self.api_client = APIClient(API_BASE_URL, VEHICLE_ID)

    # ─── YOLO Detection Thread ──────────────────────────────
    def _detection_loop(self):
        """Runs YOLO on latest frame, then sleeps 2s on detection."""
        logger.info("Detection thread started.")
        while not self.shutdown_event.is_set():
            frame = self.latest_frame
            if frame is None:
                self.shutdown_event.wait(0.05)
                continue

            try:
                # Copy the frame so main thread can keep updating
                frame_copy = frame.copy()
                detections = self.pothole_detector.detect(frame_copy)
                self.latest_detections = detections

                if len(detections) > 0:
                    det = detections[0]  # process first detection
                    self.last_report_time = time.time()
                    self.stats["new_potholes"] += 1

                    # Get GPS position (non-blocking)
                    lat, lng = 0.0, 0.0
                    if self.gps:
                        gps_data = self.gps.get_position()
                        if gps_data:
                            lat = gps_data["lat"]
                            lng = gps_data["lng"]

                    # Only send if we have a valid GPS fix
                    if lat != 0.0 or lng != 0.0:
                        self.api_client.send_pothole(
                            lat, lng,
                            severity=det["severity"],
                            confidence=det["confidence"]
                        )
                        logger.info(
                            f"POTHOLE DETECTED at ({lat:.6f}, {lng:.6f}) "
                            f"severity={det['severity']} conf={det['confidence']:.2f}"
                        )
                    else:
                        logger.warning(
                            "POTHOLE DETECTED but no GPS fix — skipping report"
                        )

                    # Buzz for 1 second
                    if self.buzzer:
                        self.buzzer.alert_pothole(BUZZER_PATTERN_POTHOLE)

                    # 2-second cooldown — wait but still check for shutdown
                    self.shutdown_event.wait(self.report_cooldown)
                else:
                    # No detection — small sleep to avoid CPU spin
                    self.shutdown_event.wait(0.1)

            except Exception as e:
                logger.error(f"Detection thread error: {e}")
                self.shutdown_event.wait(0.5)

        logger.info("Detection thread stopped.")

    # ─── Main Display Loop ──────────────────────────────────
    def run(self):
        """Main thread: capture frames + display at full speed."""
        if not self.picam2:
            logger.error("No camera available. Exiting.")
            self._shutdown()
            return

        # Create the display window
        cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_AUTOSIZE)

        # Start detection thread
        det_thread = threading.Thread(
            target=self._detection_loop, daemon=True, name="YOLODetector"
        )
        det_thread.start()

        logger.info("System Running Real-time...")

        try:
            while not self.shutdown_event.is_set():
                # 1. Capture frame (fast — just grabs from camera buffer)
                try:
                    frame_rgb = self.picam2.capture_array()
                    frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                    self.latest_frame = frame
                except Exception as e:
                    logger.error(f"Capture error: {e}")
                    self.shutdown_event.wait(0.1)
                    continue

                # 2. Draw detections on frame (uses last known detections)
                annotated = self.pothole_detector.draw_detections(
                    frame, self.latest_detections
                )

                # 3. Status overlay
                now = time.time()
                in_cooldown = (now - self.last_report_time) < self.report_cooldown
                color = (0, 0, 255) if in_cooldown else (0, 255, 0)
                status = "COOLDOWN (2s)" if in_cooldown else "SCANNING..."

                cv2.putText(
                    annotated, status, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2
                )
                cv2.putText(
                    annotated,
                    f"Potholes: {self.stats['new_potholes']}",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2
                )

                # GPS status
                if self.gps:
                    gps_pos = self.gps.get_position()
                    if gps_pos:
                        gps_text = f"GPS: {gps_pos['lat']:.5f}, {gps_pos['lng']:.5f}"
                        gps_color = (0, 255, 0)
                    else:
                        gps_text = "GPS: Waiting for fix..."
                        gps_color = (0, 165, 255)
                else:
                    gps_text = "GPS: Not connected"
                    gps_color = (0, 0, 255)
                cv2.putText(
                    annotated, gps_text, (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, gps_color, 1
                )

                # 4. Display
                cv2.imshow(WINDOW_NAME, annotated)

                # 5. Key handling — 'q', ESC, or window close button
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:  # q or ESC
                    logger.info("Quit key pressed.")
                    break

                # Check if window was closed via X button
                try:
                    if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                        logger.info("Window closed via X button.")
                        break
                except cv2.error:
                    break

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received.")

        self._shutdown()

    # ─── Clean Shutdown ─────────────────────────────────────
    def _shutdown(self):
        """Cleanly stop all hardware and exit."""
        logger.info("Shutting down...")
        self.shutdown_event.set()

        # Stop buzzer first (ensure silence)
        if self.buzzer:
            try:
                self.buzzer.force_off()
                self.buzzer.cleanup()
            except Exception:
                pass

        # Stop GPS
        if self.gps:
            try:
                self.gps.disconnect()
            except Exception:
                pass

        # Stop camera
        if self.picam2:
            try:
                self.picam2.stop()
                self.picam2.close()
            except Exception:
                pass

        # Close OpenCV windows
        cv2.destroyAllWindows()
        # Pump events so windows actually close
        for _ in range(5):
            cv2.waitKey(1)

        logger.info("System Stopped.")
        sys.exit(0)


# ─── Entry Point ────────────────────────────────────────────
if __name__ == "__main__":
    # Handle Ctrl+C gracefully
    system = RoadGuardSystem()

    def _signal_handler(sig, frame):
        system._shutdown()

    signal.signal(signal.SIGINT, _signal_handler)

    system.run()
