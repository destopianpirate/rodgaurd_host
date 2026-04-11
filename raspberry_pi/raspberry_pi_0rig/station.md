# RoadGuard Raspberry Pi Hardware Station

This document outlines the exact physical connections needed to wire the hardware modules to the Raspberry Pi 4 Model B for the RoadGuard project.

---

## 1. Neo-6M GPS Module
Uses Serial UART for communication. Mapped to `/dev/ttyS0`.

| GPS Pin | Raspberry Pi Pin | Description |
| :---: | :---: | :--- |
| **VCC** | **Pin 4** (5V) or **Pin 1** (3.3V) | Provides power to the GPS unit. |
| **GND** | **Pin 6** (GND) | Ground connection. |
| **TX** | **Pin 10 / GPIO 15** (RXD) | Transmits data from GPS to Pi. |
| **RX** | **Pin 8 / GPIO 14** (TXD) | Receives data from Pi to GPS (Optional, but good practice). |

*Note: Ensure "Serial Port" is enabled and "Serial Console" is disabled in `sudo raspi-config` settings.*

---

## 2. Active Buzzer Module
Uses basic General Purpose Input/Output (GPIO) control. Mapped to **BCM GPIO 18**.

| Buzzer Pin | Raspberry Pi Pin | Description |
| :---: | :---: | :--- |
| **VCC / +** | **Pin 2** (5V) or **Pin 17** (3.3V) | Provides power to the active buzzer. |
| **GND / -** | **Pin 14** (GND) | Ground connection. |
| **I/O / SIG** | **Pin 12 / GPIO 18** | Receives the HIGH/LOW signal to beep. |

---

## 3. Raspberry Pi Camera Module v2
Uses the dedicated high-speed Camera Serial Interface (CSI) ribbon port.

1. Locate the **CSI interface port** (labeled `CAMERA` or `CSI`) on the Raspberry Pi board (between the HDMI and audio ports). 
2. Pull up the plastic collar on the port.
3. Insert the ribbon cable with the **blue side facing the Ethernet/USB ports** (silver connectors facing the HDMI).
4. Push the plastic collar back down to lock it in place.
5. In `sudo raspi-config`, ensure the camera interface is activated under Interfacing Options.

---
*The MLX90640 Thermal Sensor lines have been intentionally removed from this wiring guide as they are no longer supported or required.*
