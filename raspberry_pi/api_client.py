"""
API Client Module — HTTP Client for Backend Server
Sends detection data, fetches nearby potholes, verifies/resolves potholes.
Supports retry logic and offline queue.
"""

import json
import os
import time
import logging
import requests
from threading import Thread, Lock

logger = logging.getLogger(__name__)


class APIClient:
    """HTTP client for the RoadGuard backend with verification support."""

    def __init__(self, base_url, vehicle_id="car-001",
                 offline_queue_file="offline_queue.json", max_queue_size=1000):
        self.base_url = base_url.rstrip('/')
        self.vehicle_id = vehicle_id
        self.offline_queue_file = offline_queue_file
        self.max_queue_size = max_queue_size
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self._lock = Lock()
        self.offline_queue = self._load_queue()
        if self.offline_queue:
            logger.info(f"Loaded {len(self.offline_queue)} items from offline queue")

    # ─── Pothole Operations ─────────────────────────────────

    def send_pothole(self, lat, lng, severity="medium", confidence=0.0,
                     description="", image_url="", detected_at=None):
        """
        Report a pothole. Server auto-verifies if one already exists nearby.
        Returns: dict with 'action' ('created' or 'verified') or None on failure.
        """
        data = {
            "lat": lat, "lng": lng,
            "severity": severity, "confidence": confidence,
            "description": description, "image_url": image_url,
            "vehicle_id": self.vehicle_id,
            "detected_at": detected_at or time.strftime('%Y-%m-%dT%H:%M:%S')
        }
        return self._send_sync("potholes", data)

    def get_nearby_potholes(self, lat, lng, radius=100):
        """
        Fetch active potholes near a GPS location from the server.
        Used by the car to know about upcoming potholes.
        
        Returns: list of nearby pothole dicts, or empty list on failure.
        """
        try:
            response = self.session.get(
                f"{self.base_url}/potholes/nearby",
                params={"lat": lat, "lng": lng, "radius": radius},
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logger.debug(f"Nearby fetch failed: {e}")
        return []

    def verify_pothole(self, pothole_id):
        """
        Confirm a known pothole is still present at its location.
        Called when camera detects a pothole near a known location.
        """
        data = {"vehicle_id": self.vehicle_id}
        try:
            response = self.session.post(
                f"{self.base_url}/potholes/{pothole_id}/verify",
                json=data, timeout=5
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ Verified pothole #{pothole_id}: {result.get('verified_count')} confirmations")
                return result
        except Exception as e:
            logger.warning(f"Verify failed: {e}")
        return None

    def resolve_pothole(self, pothole_id):
        """
        Report that a known pothole is no longer present.
        Called when car passes a known pothole location but camera doesn't detect it.
        """
        data = {"vehicle_id": self.vehicle_id}
        try:
            response = self.session.post(
                f"{self.base_url}/potholes/{pothole_id}/resolve",
                json=data, timeout=5
            )
            if response.status_code == 200:
                result = response.json()
                logger.info(f"🔧 Resolve report for pothole #{pothole_id}: {result.get('message')}")
                return result
        except Exception as e:
            logger.warning(f"Resolve failed: {e}")
        return None


    # ─── Network Layer ──────────────────────────────────────

    def _send_sync(self, endpoint, data, retry_count=2):
        """POST data synchronously with retries. Returns response JSON or None."""
        url = f"{self.base_url}/{endpoint}"
        for attempt in range(retry_count):
            try:
                response = self.session.post(url, json=data, timeout=10)
                if response.status_code in (200, 201):
                    result = response.json()
                    logger.info(f"✅ {endpoint}: {result.get('action', 'sent')} — {result.get('message', 'ok')}")
                    self._flush_queue()
                    return result
                else:
                    logger.warning(f"API returned {response.status_code}")
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error (attempt {attempt + 1}/{retry_count})")
            except requests.exceptions.Timeout:
                logger.warning(f"Timeout (attempt {attempt + 1}/{retry_count})")
            except Exception as e:
                logger.error(f"Request error: {e}")
            if attempt < retry_count - 1:
                time.sleep(0.5)

        logger.warning(f"⚠️ Queueing offline: {endpoint}")
        self._add_to_queue(endpoint, data)
        return None

    def _send_async(self, endpoint, data):
        thread = Thread(target=self._send_sync, args=(endpoint, data))
        thread.daemon = True
        thread.start()

    def _add_to_queue(self, endpoint, data):
        with self._lock:
            self.offline_queue.append({
                "endpoint": endpoint, "data": data,
                "queued_at": time.strftime('%Y-%m-%dT%H:%M:%S')
            })
            if len(self.offline_queue) > self.max_queue_size:
                self.offline_queue = self.offline_queue[-self.max_queue_size:]
            self._save_queue()

    def _flush_queue(self):
        if not self.offline_queue:
            return
        with self._lock:
            remaining = []
            for item in self.offline_queue:
                try:
                    resp = self.session.post(
                        f"{self.base_url}/{item['endpoint']}",
                        json=item['data'], timeout=5
                    )
                    if resp.status_code not in (200, 201):
                        remaining.append(item)
                except Exception:
                    remaining.append(item)
                    break
            self.offline_queue = remaining
            self._save_queue()

    def _save_queue(self):
        try:
            with open(self.offline_queue_file, 'w') as f:
                json.dump(self.offline_queue, f, indent=2)
        except Exception as e:
            logger.error(f"Queue save error: {e}")

    def _load_queue(self):
        if os.path.exists(self.offline_queue_file):
            try:
                with open(self.offline_queue_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def health_check(self):
        try:
            return self.session.get(f"{self.base_url}/health", timeout=5).status_code == 200
        except Exception:
            return False

    def get_queue_size(self):
        return len(self.offline_queue)
