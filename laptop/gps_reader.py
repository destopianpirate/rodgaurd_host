"""
GPS Reader Module — IP Geolocation
For laptop usage where hardware GPS relies on IP approximation.
"""

import time
import logging
import requests

logger = logging.getLogger(__name__)

class GPSReader:
    """Provides GPS coordinates based on IP geolocation."""

    def __init__(self, port=None, baud_rate=None):
        self.latitude = None
        self.longitude = None
        self.last_update = 0
        self.is_connected = False
        
        # Default fallback location if internet fails
        self.fallback_lat = 23.2156
        self.fallback_lng = 72.6369

    def connect(self):
        """Mock connection to GPS."""
        logger.info("GPS (IP Geolocation) initialized")
        self.is_connected = True
        self._fetch_location()
        return True

    def disconnect(self):
        """Close connection."""
        self.is_connected = False
        logger.info("GPS disconnected")

    def _fetch_location(self):
        if not self.is_connected:
            return
            
        try:
            r = requests.get('http://ip-api.com/json/')
            if r.status_code == 200:
                loc = r.json()
                if loc.get('status') == 'success':
                    self.latitude = float(loc['lat'])
                    self.longitude = float(loc['lon'])
                logger.info(f"Loaded IP Geolocation: {self.latitude}, {self.longitude}")
            else:
                raise Exception(f"Status code {r.status_code}")
        except Exception as e:
            logger.warning(f"IP Location failed ({e}). Using fallback.")
            self.latitude = self.fallback_lat
            self.longitude = self.fallback_lng
            
        self.last_update = time.time()

    def read(self):
        if self.latitude is None or self.longitude is None:
            return None

        if time.time() - self.last_update > 60:
            self.last_update = time.time()

        # Simulate walking/driving movement around the IP location!
        import random
        jitter_lat = random.uniform(-0.002, 0.002) # ~200m spread
        jitter_lng = random.uniform(-0.002, 0.002)

        return {
            "lat": self.latitude + jitter_lat,
            "lng": self.longitude + jitter_lng,
            "speed_knots": 0,
            "altitude": 0,
            "fix_quality": 1,
            "satellites": 4
        }
        
    def has_fix(self):
        return self.latitude is not None

    def get_speed_kmh(self):
        return 0.0

    def __str__(self):
        if self.has_fix():
            return f"GPS({self.latitude:.6f}, {self.longitude:.6f}) fix=1 sats=4"
        return "GPS(no fix)"

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    gps = GPSReader()
    if gps.connect():
        print("Reading GPS data...")
        data = gps.read()
        print(data)
