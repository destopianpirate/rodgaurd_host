#!/usr/bin/env python3
"""
BUZZER DIAGNOSTIC — Run this on the Raspberry Pi to figure out
what's really going on with your buzzer module.

Wiring for this test:
  VCC → Pin 2 (5V)
  GND → Pin 6 (GND)
  I/O → Pin 33 (GPIO 13)

Run:  python3 buzzer_diag.py
"""
import time

try:
    import RPi.GPIO as GPIO
except ImportError:
    print("ERROR: RPi.GPIO not found. Run this on the Raspberry Pi!")
    exit(1)

PIN = 13  # BCM pin = Physical Pin 33

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.OUT)

print("=" * 55)
print("  BUZZER DIAGNOSTIC TOOL")
print("  Wiring: VCC=5V, GND=GND, I/O=Pin33 (GPIO13)")
print("=" * 55)

# ─── TEST 1: Pin LOW ────────────────────────────
print("\n>>> TEST 1: Setting GPIO 13 to LOW...")
GPIO.output(PIN, GPIO.LOW)
answer1 = input("    Is the buzzer BEEPING or SILENT? (b/s): ").strip().lower()

# ─── TEST 2: Pin HIGH ───────────────────────────
print("\n>>> TEST 2: Setting GPIO 13 to HIGH...")
GPIO.output(PIN, GPIO.HIGH)
answer2 = input("    Is the buzzer BEEPING or SILENT? (b/s): ").strip().lower()

# ─── TEST 3: Disconnect VCC ─────────────────────
print("\n>>> TEST 3: Now DISCONNECT the VCC wire (remove it from 5V pin).")
input("    Press Enter after disconnecting VCC...")
answer3 = input("    Is the buzzer BEEPING or SILENT now? (b/s): ").strip().lower()

# ─── TEST 4: Reconnect VCC and disconnect I/O ───
print("\n>>> TEST 4: Reconnect VCC. Then DISCONNECT the I/O wire from Pin 33.")
input("    Press Enter after reconnecting VCC and disconnecting I/O...")
answer4 = input("    Is the buzzer BEEPING or SILENT now? (b/s): ").strip().lower()

# ─── RESULTS ────────────────────────────────────
GPIO.cleanup(PIN)

print("\n" + "=" * 55)
print("  RESULTS")
print("=" * 55)
print(f"  Test 1 (GPIO LOW):       {'BEEPING' if answer1 == 'b' else 'SILENT'}")
print(f"  Test 2 (GPIO HIGH):      {'BEEPING' if answer2 == 'b' else 'SILENT'}")
print(f"  Test 3 (No VCC):         {'BEEPING' if answer3 == 'b' else 'SILENT'}")
print(f"  Test 4 (No I/O, has VCC):{'BEEPING' if answer4 == 'b' else 'SILENT'}")
print("=" * 55)

if answer3 == 'b':
    print("\n⚠️  Buzzer beeps even without VCC — check wiring!")
elif answer4 == 'b':
    print("\n⚠️  Buzzer beeps just from VCC power alone!")
    print("   The I/O pin is NOT controlling the buzzer.")
    print("   FIX: Connect VCC to GPIO pin instead of 5V.")
    print("   New wiring:")
    print("     VCC → Pin 33 (GPIO 13)")
    print("     GND → Pin 6 (GND)")
    print("     I/O → Not connected (leave floating)")
elif answer1 == 's' and answer2 == 'b':
    print("\n✅  ACTIVE-HIGH buzzer confirmed!")
    print("   LOW=OFF, HIGH=ON — code should use current logic.")
elif answer1 == 'b' and answer2 == 's':
    print("\n✅  ACTIVE-LOW buzzer confirmed!")
    print("   HIGH=OFF, LOW=ON — code needs active-low logic.")
else:
    print("\n⚠️  Unexpected results. Please share these results.")

print("\nDone.")
