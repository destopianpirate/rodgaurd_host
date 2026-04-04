"""
GPS Reader Module — NEO-6M GPS via Serial UART
Reads NMEA sentences and extracts latitude, longitude, speed, and altitude.
"""

import serial
import time
import logging

logger = logging.getLogger(__name__)


class GPSReader:
    """Reads GPS coordinates from a NEO-6M module via serial UART."""

    def __init__(self, port="/dev/ttyS0", baud_rate=9600):
        self.port = port
        self.baud_rate = baud_rate
        self.serial_conn = None
        self.latitude = None
        self.longitude = None
        self.speed_knots = None
        self.altitude = None
        self.fix_quality = 0
        self.satellites = 0
        self.last_update = None

    def connect(self):
        """Open serial connection to the GPS module."""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=1
            )
            logger.info(f"GPS connected on {self.port} at {self.baud_rate} baud")
            return True
        except serial.SerialException as e:
            logger.error(f"GPS connection failed: {e}")
            return False

    def disconnect(self):
        """Close the serial connection."""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            logger.info("GPS disconnected")

    def read(self):
        """
        Read and parse NMEA sentences from GPS.
        
        Returns:
            dict: GPS data with lat, lng, speed, altitude, or None if no fix.
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            logger.warning("GPS serial not connected")
            return None

        try:
            # Read multiple lines to find GGA and RMC sentences
            for _ in range(10):
                line = self.serial_conn.readline().decode('ascii', errors='replace').strip()
                
                if line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                    self._parse_gga(line)
                elif line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                    self._parse_rmc(line)

            if self.has_fix():
                self.last_update = time.time()
                return {
                    "lat": self.latitude,
                    "lng": self.longitude,
                    "speed_knots": self.speed_knots,
                    "altitude": self.altitude,
                    "fix_quality": self.fix_quality,
                    "satellites": self.satellites
                }
            return None

        except Exception as e:
            logger.error(f"GPS read error: {e}")
            return None

    def _parse_gga(self, sentence):
        """
        Parse $GPGGA sentence for position and fix quality.
        Format: $GPGGA,time,lat,N/S,lon,E/W,quality,satellites,hdop,altitude,M,...
        """
        try:
            parts = sentence.split(',')
            if len(parts) < 10:
                return

            # Fix quality (0=invalid, 1=GPS fix, 2=DGPS)
            self.fix_quality = int(parts[6]) if parts[6] else 0
            if self.fix_quality == 0:
                return

            # Latitude
            if parts[2] and parts[3]:
                self.latitude = self._nmea_to_decimal(parts[2], parts[3])

            # Longitude
            if parts[4] and parts[5]:
                self.longitude = self._nmea_to_decimal(parts[4], parts[5])

            # Satellites
            if parts[7]:
                self.satellites = int(parts[7])

            # Altitude
            if parts[9]:
                self.altitude = float(parts[9])

        except (ValueError, IndexError) as e:
            logger.debug(f"GGA parse error: {e}")

    def _parse_rmc(self, sentence):
        """
        Parse $GPRMC sentence for speed.
        Format: $GPRMC,time,status,lat,N/S,lon,E/W,speed,course,date,...
        """
        try:
            parts = sentence.split(',')
            if len(parts) < 8:
                return

            # Status (A=active, V=void)
            if parts[2] != 'A':
                return

            # Speed in knots
            if parts[7]:
                self.speed_knots = float(parts[7])

            # Also parse lat/lng from RMC as backup
            if parts[3] and parts[4]:
                self.latitude = self._nmea_to_decimal(parts[3], parts[4])
            if parts[5] and parts[6]:
                self.longitude = self._nmea_to_decimal(parts[5], parts[6])

        except (ValueError, IndexError) as e:
            logger.debug(f"RMC parse error: {e}")

    def _nmea_to_decimal(self, coord, direction):
        """
        Convert NMEA coordinate format to decimal degrees.
        
        NMEA format: DDDMM.MMMMM (degrees + minutes)
        """
        if not coord:
            return None

        # Find the decimal point
        dot_pos = coord.index('.')
        degrees = float(coord[:dot_pos - 2])
        minutes = float(coord[dot_pos - 2:])
        decimal = degrees + minutes / 60.0

        if direction in ('S', 'W'):
            decimal = -decimal

        return decimal

    def has_fix(self):
        """Check if GPS has a valid fix."""
        return self.fix_quality > 0 and self.latitude is not None

    def get_speed_kmh(self):
        """Get speed in km/h (converted from knots)."""
        if self.speed_knots is not None:
            return self.speed_knots * 1.852
        return None

    def __str__(self):
        if self.has_fix():
            return f"GPS({self.latitude:.6f}, {self.longitude:.6f}) fix={self.fix_quality} sats={self.satellites}"
        return "GPS(no fix)"


# ─── Standalone test ─────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    from config import GPS_SERIAL_PORT, GPS_BAUD_RATE

    gps = GPSReader(GPS_SERIAL_PORT, GPS_BAUD_RATE)
    if gps.connect():
        print("Reading GPS data... (press Ctrl+C to stop)")
        try:
            while True:
                data = gps.read()
                if data:
                    print(f"  Lat: {data['lat']:.6f}, Lng: {data['lng']:.6f}, "
                          f"Speed: {gps.get_speed_kmh():.1f} km/h, "
                          f"Alt: {data['altitude']}m, Sats: {data['satellites']}")
                else:
                    print("  Waiting for GPS fix...")
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            gps.disconnect()
