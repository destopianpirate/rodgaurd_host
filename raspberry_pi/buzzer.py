"""
Buzzer Alert Module — GPIO Buzzer Control
Provides different alert patterns for pothole and animal detections.
"""

import time
import logging
import threading

logger = logging.getLogger(__name__)

try:
    from gpiozero import Buzzer as GpioBuzzer
    GPIOZERO_AVAILABLE = True
except ImportError:
    GPIOZERO_AVAILABLE = False
    logger.warning("gpiozero not available — buzzer in simulation mode")


class Buzzer:
    """Controls a GPIO buzzer with different alert patterns."""

    def __init__(self, pin=18, cooldown=5.0):
        """
        Initialize buzzer.
        
        Args:
            pin: BCM GPIO pin number the buzzer is connected to
            cooldown: Minimum seconds between alerts to prevent spam
        """
        self.pin = pin
        self.cooldown = cooldown
        self.last_alert_time = 0
        self._playing = False
        self._lock = threading.Lock()
        self._buzzer = None

        if GPIOZERO_AVAILABLE:
            try:
                self._buzzer = GpioBuzzer(self.pin, active_high=False)
                logger.info(f"Buzzer initialized on GPIO pin {pin} using gpiozero")
            except Exception as e:
                logger.error(f"Buzzer GPIO setup failed: {e}")
        else:
            logger.info("Buzzer running in simulation mode (no gpiozero)")

    def alert_pothole(self, pattern=None):
        """
        Play pothole alert pattern (triple short beep).
        
        Args:
            pattern: List of (on_seconds, off_seconds) tuples.
                     Default: [(0.2, 0.1), (0.2, 0.1), (0.2, 0.5)]
        """
        if pattern is None:
            pattern = [(0.2, 0.1), (0.2, 0.1), (0.2, 0.5)]
        self._play_pattern(pattern, "pothole")


    def _play_pattern(self, pattern, alert_type):
        """Play an alert pattern in a non-blocking thread."""
        # Check cooldown
        now = time.time()
        if now - self.last_alert_time < self.cooldown:
            logger.debug(f"Buzzer cooldown active, skipping {alert_type} alert")
            return

        # Don't overlap alerts
        if self._playing:
            return

        self.last_alert_time = now
        thread = threading.Thread(target=self._play_thread, args=(pattern, alert_type))
        thread.daemon = True
        thread.start()

    def _play_thread(self, pattern, alert_type):
        """Background thread to play the buzzer pattern."""
        with self._lock:
            self._playing = True
            try:
                logger.info(f"🔔 Buzzer alert: {alert_type}")
                for on_time, off_time in pattern:
                    self._buzzer_on()
                    time.sleep(on_time)
                    self._buzzer_off()
                    time.sleep(off_time)
            except Exception as e:
                logger.error(f"Buzzer error: {e}")
            finally:
                self._buzzer_off()
                self._playing = False

    def _buzzer_on(self):
        """Turn buzzer ON."""
        if GPIOZERO_AVAILABLE and self._buzzer:
            try:
                self._buzzer.on()
            except Exception:
                pass
        else:
            logger.debug("🔊 BEEP")

    def _buzzer_off(self):
        """Turn buzzer OFF."""
        if GPIOZERO_AVAILABLE and self._buzzer:
            try:
                self._buzzer.off()
            except Exception:
                pass

    def cleanup(self):
        """Clean up GPIO resources."""
        self._buzzer_off()
        if self._buzzer:
            self._buzzer.close()
            logger.info("Buzzer gpiozero resources cleaned up")


# ─── Standalone test ─────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    from config import BUZZER_GPIO_PIN, BUZZER_COOLDOWN

    buzzer = Buzzer(pin=BUZZER_GPIO_PIN, cooldown=BUZZER_COOLDOWN)

    print("Testing buzzer alerts...")
    print("1. Pothole alert (triple beep)")
    buzzer.alert_pothole()
    time.sleep(3)


    buzzer.cleanup()
    print("Done.")
