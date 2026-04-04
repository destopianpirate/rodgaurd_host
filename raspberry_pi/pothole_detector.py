"""
Pothole Detector Module — YOLOv8 (Ultralytics)
Runs pothole detection on camera frames using a YOLO model.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    logger.warning("ultralytics not installed. Run: pip install ultralytics")

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    logger.warning("opencv-python not installed. Run: pip install opencv-python")


class PotholeDetector:
    """Detects potholes in camera frames using YOLOv8."""

    def __init__(self, model_path="yolov8n.pt", confidence_threshold=0.5, severity_thresholds=None, use_cloud_api=False, roboflow_model_id=None):
        """
        Initialize the pothole detector.
        
        Args:
            model_path: Path to YOLOv8 model weights (.pt file)
            confidence_threshold: Minimum confidence to accept a detection
            severity_thresholds: Dict of severity level -> area ratio thresholds
        """
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.model = None
        self.severity_thresholds = severity_thresholds or {
            "critical": 0.15,
            "high": 0.08,
            "medium": 0.03,
        }

        self.use_cloud_api = use_cloud_api
        self.roboflow_model_id = roboflow_model_id

        if self.use_cloud_api:
            logger.info(f"Initializing Roboflow Hosted API config for model: {self.roboflow_model_id}")
            self.model = "CLOUD_API"
            
            try:
                from inference_sdk import InferenceHTTPClient
                self.client = InferenceHTTPClient(
                    api_url="https://serverless.roboflow.com",
                    api_key=ROBOFLOW_API_KEY
                )
                logger.info("InferenceHTTPClient initialized successfully.")
            except ImportError:
                logger.error("inference_sdk is not installed. Cloud API will fail.")
                self.client = None
            return

        if YOLO_AVAILABLE:
            try:
                self.model = YOLO(model_path)
                logger.info(f"YOLO model loaded: {model_path}")
                # Log model class names
                if hasattr(self.model, 'names'):
                    logger.info(f"Model classes: {self.model.names}")
            except Exception as e:
                logger.error(f"Failed to load YOLO model: {e}")
        else:
            logger.error("YOLO not available — install ultralytics package")

    def detect(self, frame):
        """
        Run pothole detection on a camera frame.
        
        Args:
            frame: numpy array (BGR image from OpenCV)
            
        Returns:
            list of detections, each a dict with:
                - bbox: (x1, y1, x2, y2) bounding box
                - confidence: float 0-1
                - severity: str ('low', 'medium', 'high', 'critical')
                - area_ratio: float (area of bbox / area of frame)
                - class_name: str
        """
        if self.model is None:
            logger.warning("YOLO model not loaded, skipping detection")
            return []

        if frame is None or not isinstance(frame, np.ndarray):
            return []

        try:
            detections = []
            frame_area = frame.shape[0] * frame.shape[1]

            if getattr(self, 'use_cloud_api', False):
                import time
                start_api_time = time.time()
                
                # --- NEW API USING INFERENCE SDK ---
                if hasattr(self, 'client') and self.client is not None:
                    try:
                        result = self.client.infer(frame, model_id=self.roboflow_model_id)
                        preds = result.get("predictions", [])
                        
                        for pred in preds:
                            confidence = float(pred.get("confidence", 0.0))
                            if confidence < self.confidence_threshold:
                                continue
                            
                            class_name = pred.get("class", "unknown")
                            cx, cy, w, h = pred["x"], pred["y"], pred["width"], pred["height"]
                            x1, y1, x2, y2 = cx - (w / 2), cy - (h / 2), cx + (w / 2), cy + (h / 2)
                            
                            # --- ACTIVE LEARNING LOGIC ---
                            if ROBOFLOW_AVAILABLE and 0.30 <= confidence <= 0.60:
                                logger.info(f"Unsure detection ({confidence:.2f}). Uploading to Roboflow for Active Learning...")
                                self._upload_to_roboflow(frame)
                                
                            area_ratio = (w * h) / frame_area if frame_area > 0 else 0
                            severity = self._classify_severity(area_ratio)
                            
                            detections.append({
                                "bbox": (int(x1), int(y1), int(x2), int(y2)),
                                "confidence": round(confidence, 3),
                                "severity": severity,
                                "area_ratio": round(area_ratio, 4),
                                "class_name": class_name
                            })
                        logger.debug(f"SDK API request took: {time.time() - start_api_time:.3f} seconds")
                    except Exception as e:
                        logger.error(f"Inference SDK Error: {e}")
                
                # --- OLDER API ALTLERNATIVE (COMMENTED OUT) ---
                '''
                import base64
                import requests
                
                # Resize frame to reduce API payload size (max 640px)
                height, width = frame.shape[:2]
                max_dim = 640
                scale = 1.0
                if max(height, width) > max_dim:
                    scale = max_dim / max(height, width)
                    img_to_encode = cv2.resize(frame, (int(width * scale), int(height * scale)))
                else:
                    img_to_encode = frame
                    
                # Encode with 80% JPEG quality
                ret, buffer = cv2.imencode('.jpg', img_to_encode, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    img_str = base64.b64encode(buffer).decode('utf-8')
                    url = f"https://detect.roboflow.com/{self.roboflow_model_id}?api_key={ROBOFLOW_API_KEY}"
                    
                    try:
                        response = requests.post(url, data=img_str, headers={"Content-Type": "application/x-www-form-urlencoded"})
                        if response.status_code == 200:
                            preds = response.json().get("predictions", [])
                            for pred in preds:
                                confidence = float(pred.get("confidence", 0.0))
                                if confidence < self.confidence_threshold:
                                    continue
                                
                                class_name = pred.get("class", "unknown")
                                
                                # Scale coordinates back up to original frame size
                                cx = pred["x"] / scale
                                cy = pred["y"] / scale
                                w = pred["width"] / scale
                                h = pred["height"] / scale
                                
                                x1, y1, x2, y2 = cx - (w / 2), cy - (h / 2), cx + (w / 2), cy + (h / 2)
                                
                                # --- ACTIVE LEARNING LOGIC ---
                                if ROBOFLOW_AVAILABLE and 0.30 <= confidence <= 0.60:
                                    logger.info(f"Unsure detection ({confidence:.2f}). Uploading to Roboflow for Active Learning...")
                                    self._upload_to_roboflow(frame)
                                    
                                area_ratio = (w * h) / frame_area if frame_area > 0 else 0
                                severity = self._classify_severity(area_ratio)
                                
                                detections.append({
                                    "bbox": (int(x1), int(y1), int(x2), int(y2)),
                                    "confidence": round(confidence, 3),
                                    "severity": severity,
                                    "area_ratio": round(area_ratio, 4),
                                    "class_name": class_name
                                })
                    except Exception as e:
                        logger.error(f"Cloud API request failed: {e}")
                '''
            else:
                # Run local inference
                results = self.model(frame, conf=self.confidence_threshold, verbose=False)

                for result in results:
                    boxes = result.boxes
                    if boxes is None:
                        continue

                    for i in range(len(boxes)):
                        # Get class name
                        cls_id = int(boxes.cls[i])
                        class_name = self.model.names.get(cls_id, "unknown")

                        confidence = float(boxes.conf[i])

                        # Bounding box
                        x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                        bbox_area = (x2 - x1) * (y2 - y1)
                        area_ratio = bbox_area / frame_area if frame_area > 0 else 0

                        # Classify severity based on size
                        severity = self._classify_severity(area_ratio)

                        detections.append({
                            "bbox": (int(x1), int(y1), int(x2), int(y2)),
                            "confidence": round(confidence, 3),
                            "severity": severity,
                            "area_ratio": round(area_ratio, 4),
                            "class_name": class_name
                        })

            if detections:
                logger.info(f"Detected {len(detections)} pothole(s): "
                           f"{[d['severity'] for d in detections]}")

            return detections

        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []

    def _classify_severity(self, area_ratio):
        """Classify pothole severity based on bounding box area ratio."""
        if area_ratio >= self.severity_thresholds.get("critical", 0.15):
            return "critical"
        elif area_ratio >= self.severity_thresholds.get("high", 0.08):
            return "high"
        elif area_ratio >= self.severity_thresholds.get("medium", 0.03):
            return "medium"
        else:
            return "low"

    def draw_detections(self, frame, detections):
        """
        Draw bounding boxes and labels on the frame (for debugging/display).
        
        Args:
            frame: Original BGR image
            detections: List of detection dicts
            
        Returns:
            Annotated frame
        """
        if not CV2_AVAILABLE or frame is None:
            return frame

        annotated = frame.copy()
        colors = {
            "critical": (0, 0, 255),    # Red
            "high": (0, 128, 255),      # Orange
            "medium": (0, 255, 255),    # Yellow
            "low": (0, 255, 0)          # Green
        }

        for det in detections:
            x1, y1, x2, y2 = det["bbox"]
            color = colors.get(det["severity"], (255, 255, 255))
            confidence = det["confidence"]
            severity = det["severity"]

            # Draw box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Draw label
            label = f"Pothole {severity} ({confidence:.0%})"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            cv2.rectangle(annotated, (x1, y1 - label_size[1] - 8), 
                         (x1 + label_size[0] + 4, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 2, y1 - 4),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return annotated

    def is_ready(self):
        """Check if the detector is ready."""
        return self.model is not None


# ─── Standalone test ─────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    try:
        from config import (
            YOLO_MODEL_PATH, 
            POTHOLE_CONFIDENCE_THRESHOLD, 
            SEVERITY_THRESHOLDS,
            USE_CLOUD_API,
            ROBOFLOW_MODEL_ID
        )
    except ImportError:
        YOLO_MODEL_PATH = "yolov8n.pt"
        POTHOLE_CONFIDENCE_THRESHOLD = 0.5
        SEVERITY_THRESHOLDS = None
        USE_CLOUD_API = False
        ROBOFLOW_MODEL_ID = None

    detector = PotholeDetector(
        model_path=YOLO_MODEL_PATH,
        confidence_threshold=POTHOLE_CONFIDENCE_THRESHOLD,
        severity_thresholds=SEVERITY_THRESHOLDS,
        use_cloud_api=USE_CLOUD_API,
        roboflow_model_id=ROBOFLOW_MODEL_ID
    )

    if detector.is_ready() and CV2_AVAILABLE:
        print("Testing with webcam... (press 'q' to quit)")
        
        # Force DirectShow on Windows to prevent MSMF grabFrame crash during high framerate thread polls
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(0)
            
        import time
        import threading
        
        global latest_frame, current_detections, detecting, running
        latest_frame = None
        current_detections = []
        detecting = False
        running = True
        
        # Thread 1: Constantly read the freshest frame from camera hardware
        def camera_thread():
            global latest_frame, running
            while running:
                ret, frame = cap.read()
                if ret:
                    latest_frame = frame.copy()
                
                # Tiny sleep prevents overwhelming the USB controller / DShow backend
                time.sleep(0.01)
                    
        # Thread 2: Constantly process the freshest frame through the AI model
        def detection_thread():
            global latest_frame, current_detections, detecting, running
            while running:
                if latest_frame is None:
                    time.sleep(0.01)
                    continue
                    
                frame_to_detect = latest_frame.copy()
                detecting = True
                
                # Run the Cloud API or Local YOLO
                new_detections = detector.detect(frame_to_detect)
                
                # Only update if we didn't crash
                current_detections = new_detections
                detecting = False
                
        # Start both background threads
        threading.Thread(target=camera_thread, daemon=True).start()
        threading.Thread(target=detection_thread, daemon=True).start()

        # Main Thread: Only handling smooth UI rendering
        while True:
            if latest_frame is not None:
                # Always draw on the absolutely newest frame
                display_frame = latest_frame.copy()
                
                # Draw whatever the last known detections look like
                annotated = detector.draw_detections(display_frame, current_detections)
                
                if detecting:
                    cv2.putText(annotated, "Detecting...", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                               
                cv2.imshow("Pothole Detection", annotated)

            # 1ms wait is required for cv2.imshow to update
            if cv2.waitKey(1) & 0xFF == ord('q'):
                running = False
                break
                
        # Cleanup
        cap.release()
        cv2.destroyAllWindows()
    else:
        print("Detector not ready or OpenCV not available.")
import sys
print("Python path:", sys.executable)