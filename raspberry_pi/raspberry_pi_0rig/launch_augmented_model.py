"""
Launch Augmented Pothole Model — RoadGuard
==========================================
Standalone launcher for the NEW blur-augmented pothole detection model.
This does NOT replace the original model (best.pt). It uses the newly
trained model from: runs/detect/pothole_blur_augmented2/weights/best.pt

Usage (from the raspberry_pi directory):
    python launch_augmented_model.py

Press 'q' in the video window to quit.
"""

import os
import sys
import time
import logging
import threading
import cv2
import numpy as np

# ─── RoadGuard Modules ──────────────────────────────────────
from config import BUZZER_GPIO_PIN, BUZZER_COOLDOWN, BUZZER_PATTERN_POTHOLE
from buzzer import Buzzer

# ─── Setup Logging ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AugmentedModel")

# ─── Resolve Model Path ────────────────────────────────────
# The new augmented model lives in the training output directory.
# This path is relative to the project root (one level above raspberry_pi/).
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
AUGMENTED_MODEL_PATH = os.path.join(
    PROJECT_ROOT, "runs", "detect", "pothole_blur_augmented2", "weights", "best.pt"
)

# Fallback: also check if someone copied it locally
LOCAL_COPY = os.path.join(SCRIPT_DIR, "best_augmented.pt")

def get_model_path():
    """Find the augmented model, checking known locations."""
    if os.path.isfile(AUGMENTED_MODEL_PATH):
        return AUGMENTED_MODEL_PATH
    if os.path.isfile(LOCAL_COPY):
        return LOCAL_COPY
    return None


# ─── Main ───────────────────────────────────────────────────
def main():
    model_path = get_model_path()
    if model_path is None:
        logger.error(
            "❌ Augmented model not found!\n"
            f"   Expected at: {AUGMENTED_MODEL_PATH}\n"
            f"   Or local:    {LOCAL_COPY}\n"
            "   Make sure the training run has completed successfully."
        )
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("  RoadGuard — Augmented Pothole Model Launcher")
    logger.info(f"  Model: {model_path}")
    logger.info("=" * 60)

    # ── Import dependencies ──────────────────────────────────
    try:
        from ultralytics import YOLO
    except ImportError:
        logger.error("ultralytics is not installed. Run: pip install ultralytics")
        sys.exit(1)

    try:
        import cv2
    except ImportError:
        logger.error("opencv-python is not installed. Run: pip install opencv-python")
        sys.exit(1)

    # ── Load Model ───────────────────────────────────────────
    logger.info("Loading augmented model...")
    model = YOLO(model_path)
    logger.info(f"✅ Model loaded successfully!")
    if hasattr(model, 'names'):
        logger.info(f"   Classes: {model.names}")

    # ── Detection Config ─────────────────────────────────────
    CONFIDENCE_THRESHOLD = 0.5
    DETECTION_COOLDOWN = 2.0  # seconds to wait after a detection
    SEVERITY_THRESHOLDS = {"critical": 0.15, "high": 0.08, "medium": 0.03}

    SEVERITY_COLORS = {
        "critical": (0, 0, 255),     # Red
        "high":     (0, 128, 255),   # Orange
        "medium":   (0, 255, 255),   # Yellow
        "low":      (0, 255, 0),     # Green
    }

    def classify_severity(area_ratio):
        if area_ratio >= SEVERITY_THRESHOLDS["critical"]:
            return "critical"
        elif area_ratio >= SEVERITY_THRESHOLDS["high"]:
            return "high"
        elif area_ratio >= SEVERITY_THRESHOLDS["medium"]:
            return "medium"
        return "low"

    # ── Open Camera ──────────────────────────────────────────
    logger.info("Opening camera...")
    # Try DirectShow on Windows first to avoid MSMF issues
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        logger.error("❌ Could not open camera!")
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    logger.info("📷 Camera opened. Press 'q' in the video window to quit.\n")

    # ── Initialize Buzzer ────────────────────────────────────
    buzzer = None
    try:
        buzzer = Buzzer(BUZZER_GPIO_PIN, BUZZER_COOLDOWN)
        buzzer.force_off()
        logger.info("🔔 Buzzer initialized: OK")
    except Exception as e:
        logger.warning(f"⚠️ Buzzer initialization failed: {e}")

    # ── Threaded Architecture (same as pothole_detector.py) ──
    latest_frame = None
    current_detections = []
    detecting = False
    running = True
    frame_lock = threading.Lock()
    det_lock = threading.Lock()

    def camera_thread():
        nonlocal latest_frame, running
        while running:
            ret, frame = cap.read()
            if ret:
                with frame_lock:
                    latest_frame = frame.copy()
            time.sleep(0.01)

    def detection_thread():
        nonlocal latest_frame, current_detections, detecting, running
        while running:
            with frame_lock:
                frame = latest_frame.copy() if latest_frame is not None else None

            if frame is None:
                time.sleep(0.01)
                continue

            detecting = True
            try:
                results = model(frame, conf=CONFIDENCE_THRESHOLD, verbose=False)
                frame_area = frame.shape[0] * frame.shape[1]
                dets = []

                for result in results:
                    boxes = result.boxes
                    if boxes is None:
                        continue
                    for i in range(len(boxes)):
                        cls_id = int(boxes.cls[i])
                        class_name = model.names.get(cls_id, "unknown")
                        confidence = float(boxes.conf[i])
                        x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                        bbox_area = (x2 - x1) * (y2 - y1)
                        area_ratio = bbox_area / frame_area if frame_area > 0 else 0
                        severity = classify_severity(area_ratio)

                        dets.append({
                            "bbox": (int(x1), int(y1), int(x2), int(y2)),
                            "confidence": round(confidence, 3),
                            "severity": severity,
                            "area_ratio": round(area_ratio, 4),
                            "class_name": class_name,
                        })

                with det_lock:
                    current_detections = dets

                if dets:
                    summary = [(d['class_name'], d['severity'], f"{d['confidence']:.0%}") for d in dets]
                    logger.info(f"Detected {len(dets)} pothole(s): {summary}")
                    
                    # Trigger buzzer alert
                    if buzzer:
                        buzzer.alert_pothole(BUZZER_PATTERN_POTHOLE)
                    
                    # 2-second cooldown (just like main.py)
                    time.sleep(DETECTION_COOLDOWN)
            except Exception as e:
                logger.error(f"Detection error: {e}")

            detecting = False

    # Start background threads
    threading.Thread(target=camera_thread, daemon=True).start()
    threading.Thread(target=detection_thread, daemon=True).start()

    # ── Main Display Loop ────────────────────────────────────
    while True:
        with frame_lock:
            frame = latest_frame.copy() if latest_frame is not None else None

        if frame is not None:
            with det_lock:
                dets = list(current_detections)

            # Draw detections
            for det in dets:
                x1, y1, x2, y2 = det["bbox"]
                color = SEVERITY_COLORS.get(det["severity"], (255, 255, 255))
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                label = f"{det['class_name']} {det['severity']} ({det['confidence']:.0%})"
                label_sz = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                cv2.rectangle(frame, (x1, y1 - label_sz[1] - 8),
                              (x1 + label_sz[0] + 4, y1), color, -1)
                cv2.putText(frame, label, (x1 + 2, y1 - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # Status overlay
            status = "DETECTING..." if detecting else "READY"
            status_color = (0, 255, 255) if detecting else (0, 255, 0)
            cv2.putText(frame, f"[AUGMENTED MODEL] {status}", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)

            cv2.imshow("RoadGuard — Augmented Pothole Model", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            running = False
            break

    # ── Cleanup ──────────────────────────────────────────────
    cap.release()
    cv2.destroyAllWindows()
    if buzzer:
        buzzer.cleanup()
    logger.info("👋 Augmented model launcher shut down.")


if __name__ == "__main__":
    main()
