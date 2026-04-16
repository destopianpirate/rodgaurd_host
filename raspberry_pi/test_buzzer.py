import time
import sys

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("Error: RPi.GPIO is required. Run: pip install RPi.GPIO")
    sys.exit(1)

# The pin we are testing
TEST_PIN = 13

print("--- BUZZER HARDWARE TEST ---")
print("Make sure your wiring is:")
print("  VCC -> Pin 2 or Pin 4 (5V)")
print("  GND -> Pin 6 (Ground)")
print(f"  I/O -> Pin 33 (GPIO {TEST_PIN})")
print("----------------------------\n")

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(TEST_PIN, GPIO.OUT)

try:
    print("TEST 1: Driving pin LOW (0V)...")
    GPIO.output(TEST_PIN, GPIO.LOW)
    print("  -> Does it beep loudly? (If yes, you have an Active-Low buzzer)")
    time.sleep(4)

    print("\nTEST 2: Driving pin HIGH (3.3V)...")
    GPIO.output(TEST_PIN, GPIO.HIGH)
    print("  -> Does it beep loudly? (If yes, you have an Active-High buzzer)")
    print("  -> Does it only make a weak hum? (Voltage mismatch)")
    time.sleep(4)

    print("\nTest complete. Cleaning up.")
    GPIO.cleanup()

except KeyboardInterrupt:
    print("\nTest cancelled.")
    GPIO.cleanup()
