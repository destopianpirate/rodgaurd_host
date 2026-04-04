"""
Buzzer Alert Module — Windows Laptop Buzzer Control
Provides different alert patterns for pothole and animal detections using winsound.
"""

import time
import logging
import threading

logger = logging.getLogger(__name__)

try:
    import winsound
    WINSOUND_AVAILABLE = True
except ImportError:
    WINSOUND_AVAILABLE = False
    logger.warning("winsound not available — buzzer in simulation mode")

class Buzzer:
    """Controls a Windows speaker buzzer with different alert patterns."""

    def __init__(self, pin=None, cooldown=5.0):
        """
        Initialize buzzer.
        
        Args:
            pin: Ignored on Windows.
            cooldown: Minimum seconds between alerts to prevent spam
        """
        self.cooldown = cooldown
        self.last_alert_time = 0
        self._playing = False
        self._lock = threading.Lock()
        
        if WINSOUND_AVAILABLE:
            logger.info("Buzzer initialized on Windows speaker")
        else:
            logger.info("Buzzer running in simulation mode (no winsound)")

    def alert_pothole(self, pattern=None):
        if pattern is None:
            pattern = [(0.2, 0.1), (0.2, 0.1), (0.2, 0.5)]
        self._play_pattern(pattern, "pothole", freq=1000)

    def alert_animal(self, pattern=None):
        if pattern is None:
            pattern = [(0.5, 0.2), (0.5, 0.5)]
        self._play_pattern(pattern, "animal", freq=600)
        
    def alert_verified(self, pattern=None):
        if pattern is None:
            pattern = [(0.1, 0.1), (0.1, 0.3)]
        self._play_pattern(pattern, "verified", freq=1500)

    def _play_pattern(self, pattern, alert_type, freq=1000):
        """Play an alert pattern in a non-blocking thread."""
        now = time.time()
        if now - self.last_alert_time < self.cooldown:
            logger.debug(f"Buzzer cooldown active, skipping {alert_type} alert")
            return

        if self._playing:
            return

        self.last_alert_time = now
        thread = threading.Thread(target=self._play_thread, args=(pattern, alert_type, freq))
        thread.daemon = True
        thread.start()

    def _play_thread(self, pattern, alert_type, freq):
        """Background thread to play the buzzer pattern."""
        with self._lock:
            self._playing = True
            try:
                logger.info(f"🔔 Buzzer alert: {alert_type}")
                for on_time, off_time in pattern:
                    if WINSOUND_AVAILABLE:
                        winsound.Beep(freq, int(on_time * 1000))
                    else:
                        logger.debug("🔊 BEEP (simulated)")
                    time.sleep(off_time)
            except Exception as e:
                logger.error(f"Buzzer error: {e}")
            finally:
                self._playing = False

    def cleanup(self):
        pass

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    buzzer = Buzzer(cooldown=0)

    print("Testing buzzer alerts...")
    print("1. Pothole alert (triple beep)")
    buzzer.alert_pothole()
    time.sleep(2)

    print("2. Animal alert (double long beep)")
    buzzer.alert_animal()
    time.sleep(2)
    
    print("3. Verified alert")
    buzzer.alert_verified()
    time.sleep(2)

    print("Done.")
