"""
Buzzer Alert Module — GPIO Buzzer Control
Provides different alert patterns for pothole detections.
Guarantees buzzer is OFF at initialization and cleanup.

This module controls a 3-pin active buzzer module (VCC=5V, GND, I/O)
by toggling the GPIO pin between INPUT mode (high-impedance = silent)
and OUTPUT LOW mode (current sink = buzzing).
"""

import time
import logging
import threading

logger = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logger.warning("RPi.GPIO not available — buzzer in simulation mode")


class Buzzer:
    """Controls a GPIO buzzer with different alert patterns."""

    def __init__(self, pin=13, cooldown=2.0):
        """
        Initialize buzzer. Guarantees buzzer is OFF after init.

        Args:
            pin: BCM GPIO pin number the buzzer is connected to
            cooldown: Minimum seconds between alerts to prevent spam
        """
        self.pin = pin
        self.cooldown = cooldown
        self.last_alert_time = 0
        self._playing = False
        self._lock = threading.Lock()
        self._current_thread = None

        if GPIO_AVAILABLE:
            try:
                GPIO.setwarnings(False)
                GPIO.setmode(GPIO.BCM)
                # Set as INPUT (high-impedance) = buzzer OFF (like disconnecting the wire)
                GPIO.setup(self.pin, GPIO.IN)
                logger.info(f"Buzzer initialized on GPIO {pin} — SILENT (INPUT mode)")
            except Exception as e:
                logger.error(f"Buzzer GPIO setup failed: {e}")
        else:
            logger.info("Buzzer running in simulation mode (no GPIO)")

    def force_off(self):
        """Force the buzzer OFF immediately. Call at startup and shutdown."""
        self._playing = False
        if GPIO_AVAILABLE:
            try:
                # INPUT mode = high-impedance = pin is "disconnected" = buzzer silent
                GPIO.setup(self.pin, GPIO.IN)
            except Exception:
                pass

    def alert_pothole(self, pattern=None):
        """
        Play pothole alert pattern.

        Args:
            pattern: List of (on_seconds, off_seconds) tuples.
                     Default: [(1.0, 0.0)] — single 1-second buzz
        """
        if pattern is None:
            pattern = [(1.0, 0.0)]
        self._play_pattern(pattern, "pothole")

    def alert_animal(self, pattern=None):
        """
        Play animal alert pattern (double long beep).

        Args:
            pattern: List of (on_seconds, off_seconds) tuples.
                     Default: [(0.5, 0.2), (0.5, 0.5)]
        """
        if pattern is None:
            pattern = [(0.5, 0.2), (0.5, 0.5)]
        self._play_pattern(pattern, "animal")

    def _play_pattern(self, pattern, alert_type):
        """Play an alert pattern in a non-blocking thread."""
        now = time.time()
        if now - self.last_alert_time < self.cooldown:
            logger.debug(f"Buzzer cooldown active, skipping {alert_type} alert")
            return

        if self._playing:
            return

        self.last_alert_time = now
        thread = threading.Thread(
            target=self._play_thread, args=(pattern, alert_type),
            daemon=True, name="BuzzerAlert"
        )
        self._current_thread = thread
        thread.start()

    def _play_thread(self, pattern, alert_type):
        """Background thread to play the buzzer pattern."""
        with self._lock:
            self._playing = True
            try:
                logger.info(f"Buzzer alert: {alert_type}")
                for on_time, off_time in pattern:
                    if not self._playing:
                        break
                    self._buzzer_on()
                    time.sleep(on_time)
                    self._buzzer_off()
                    if off_time > 0:
                        time.sleep(off_time)
            except Exception as e:
                logger.error(f"Buzzer error: {e}")
            finally:
                self._buzzer_off()
                self._playing = False

    def _buzzer_on(self):
        """Turn buzzer ON — switch pin to OUTPUT LOW (current sink)."""
        if GPIO_AVAILABLE:
            try:
                GPIO.setup(self.pin, GPIO.OUT)
                GPIO.output(self.pin, GPIO.LOW)
            except Exception:
                pass
        else:
            logger.debug("BEEP (simulated)")

    def _buzzer_off(self):
        """Turn buzzer OFF — switch pin to INPUT (high-impedance = disconnected)."""
        if GPIO_AVAILABLE:
            try:
                GPIO.setup(self.pin, GPIO.IN)
            except Exception:
                pass

    def cleanup(self):
        """Clean up GPIO resources. Ensures buzzer is OFF."""
        self._playing = False
        self._buzzer_off()
        time.sleep(0.05)
        self._buzzer_off()
        if GPIO_AVAILABLE:
            try:
                GPIO.cleanup(self.pin)
                logger.info("Buzzer GPIO cleaned up")
            except Exception:
                pass


# ─── Standalone test ─────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 50)
    print("  BUZZER TEST — INPUT/OUTPUT toggle method")
    print("  VCC=5V, GND=GND, I/O=Pin33 (GPIO13)")
    print("=" * 50)

    buzzer = Buzzer(pin=13, cooldown=0)

    print("\n1. Buzzer should be SILENT right now.")
    input("   Press Enter to test a 1-second beep...")

    buzzer._buzzer_on()
    print("   -> BEEP! (1 second)")
    time.sleep(1.0)
    buzzer._buzzer_off()
    print("   -> Silent.")

    time.sleep(1)

    print("\n2. Testing alert_pothole pattern...")
    buzzer.alert_pothole([(1.0, 0.0)])
    time.sleep(3)

    buzzer.cleanup()
    print("\nDone. Buzzer should be completely silent now.")
