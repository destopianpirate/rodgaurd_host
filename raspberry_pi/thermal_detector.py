"""
Thermal Detector Module — MLX90640 Thermal Camera
Reads thermal data via I2C and detects warm-bodied stray animals.
"""

import time
import logging
# import numpy as np

logger = logging.getLogger(__name__)

try:
    import board
    import busio
    import adafruit_mlx90640
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False
    logger.warning("MLX90640 libraries not installed. Run: pip install adafruit-circuitpython-mlx90640")


class ThermalDetector:
    """Detects stray animals using the MLX90640 thermal camera."""

    # MLX90640 has 32x24 pixel resolution = 768 pixels
    FRAME_WIDTH = 32
    FRAME_HEIGHT = 24

    def __init__(self, temp_min=30.0, temp_max=42.0, min_blob_pixels=8, refresh_rate=2):
        """
        Initialize the thermal detector.
        
        Args:
            temp_min: Minimum temperature (°C) to consider as animal body
            temp_max: Maximum temperature (°C) — filter out hot engines, etc.
            min_blob_pixels: Minimum warm pixel count to classify as an animal
            refresh_rate: MLX90640 refresh rate in Hz
        """
        self.temp_min = temp_min
        self.temp_max = temp_max
        self.min_blob_pixels = min_blob_pixels
        self.refresh_rate = refresh_rate
        self.mlx = None
        self.frame = [0] * 768  # 32 x 24 pixels

        if MLX_AVAILABLE:
            try:
                import board
                import busio
                # On Raspberry Pi, use I2C bus 1 (GPIO 2=SDA, GPIO 3=SCL)
                i2c = busio.I2C(board.D3, board.D2, frequency=400000)
                self.mlx = adafruit_mlx90640.MLX90640(i2c)
                self.mlx.refresh_rate = self._get_refresh_rate(refresh_rate)
                logger.info(f"MLX90640 initialized (refresh rate: {refresh_rate} Hz)")
            except Exception as e:
                logger.error(f"Failed to initialize MLX90640: {e}")
        else:
            logger.warning("MLX90640 not available — running in simulation mode")

    def _get_refresh_rate(self, rate):
        """Map Hz value to MLX90640 refresh rate constant."""
        rate_map = {
            1: adafruit_mlx90640.RefreshRate.REFRESH_1_HZ,
            2: adafruit_mlx90640.RefreshRate.REFRESH_2_HZ,
            4: adafruit_mlx90640.RefreshRate.REFRESH_4_HZ,
            8: adafruit_mlx90640.RefreshRate.REFRESH_8_HZ,
            16: adafruit_mlx90640.RefreshRate.REFRESH_16_HZ,
            32: adafruit_mlx90640.RefreshRate.REFRESH_32_HZ,
        }
        return rate_map.get(rate, adafruit_mlx90640.RefreshRate.REFRESH_2_HZ)

    def scan(self):
        """
        Scan the thermal camera and detect animals.
        
        Returns:
            list of detections, each a dict with:
                - avg_temperature: Average temperature of the warm blob
                - max_temperature: Maximum temperature detected
                - warm_pixel_count: Number of pixels in the warm range
                - animal_type: Estimated animal type ('unknown' by default)
                - confidence: Detection confidence
        """
        thermal_data = self._read_frame()
        if thermal_data is None:
            return []

        return self._analyze_thermal(thermal_data)

    def _read_frame(self):
        """Read a single thermal frame from the MLX90640."""
        if self.mlx is not None:
            try:
                self.mlx.getFrame(self.frame)
                return np.array(self.frame).reshape(self.FRAME_HEIGHT, self.FRAME_WIDTH)
            except Exception as e:
                logger.error(f"Thermal frame read error: {e}")
                return None
        else:
            # Simulation mode — return None (no detections)
            return None

    def _analyze_thermal(self, thermal_frame):
        """
        Analyze thermal data for animal-like heat signatures.
        
        Logic:
        1. Find pixels within the animal body temperature range
        2. Count connected warm pixels (simple blob detection)
        3. If blob is large enough, classify as animal detection
        """
        detections = []

        # Create mask of pixels within animal body temp range
        warm_mask = (thermal_frame >= self.temp_min) & (thermal_frame <= self.temp_max)
        warm_count = np.sum(warm_mask)

        if warm_count < self.min_blob_pixels:
            return detections

        # Get temperatures of warm pixels
        warm_temps = thermal_frame[warm_mask]
        avg_temp = float(np.mean(warm_temps))
        max_temp = float(np.max(warm_temps))
        min_temp = float(np.min(warm_temps))

        # Simple blob analysis using connected components
        blobs = self._find_blobs(warm_mask)

        for blob in blobs:
            if blob["pixel_count"] < self.min_blob_pixels:
                continue

            # Calculate confidence based on temperature consistency and blob size
            temp_consistency = 1.0 - (np.std(thermal_frame[blob["mask"]]) / 5.0)
            size_factor = min(blob["pixel_count"] / 30.0, 1.0)  # Normalize to ~30 pixels
            confidence = max(0.0, min(1.0, (temp_consistency + size_factor) / 2.0))

            # Estimate animal type based on blob size
            animal_type = self._estimate_animal_type(blob["pixel_count"])

            blob_temps = thermal_frame[blob["mask"]]
            detections.append({
                "avg_temperature": round(float(np.mean(blob_temps)), 1),
                "max_temperature": round(float(np.max(blob_temps)), 1),
                "warm_pixel_count": blob["pixel_count"],
                "animal_type": animal_type,
                "confidence": round(confidence, 2),
                "centroid": blob["centroid"]
            })

        if detections:
            logger.info(f"Thermal scan: {len(detections)} animal(s) detected. "
                       f"Avg temps: {[d['avg_temperature'] for d in detections]}")

        return detections

    def _find_blobs(self, mask):
        """
        Simple connected component labeling (4-connectivity).
        Returns list of blob dicts with pixel_count, mask, and centroid.
        """
        visited = np.zeros_like(mask, dtype=bool)
        blobs = []

        for y in range(mask.shape[0]):
            for x in range(mask.shape[1]):
                if mask[y, x] and not visited[y, x]:
                    # BFS to find connected component
                    blob_mask = np.zeros_like(mask, dtype=bool)
                    queue = [(y, x)]
                    visited[y, x] = True
                    pixels = []

                    while queue:
                        cy, cx = queue.pop(0)
                        blob_mask[cy, cx] = True
                        pixels.append((cy, cx))

                        # Check 4-connected neighbors
                        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            ny, nx = cy + dy, cx + dx
                            if (0 <= ny < mask.shape[0] and 0 <= nx < mask.shape[1]
                                    and mask[ny, nx] and not visited[ny, nx]):
                                visited[ny, nx] = True
                                queue.append((ny, nx))

                    # Calculate centroid
                    if pixels:
                        avg_y = sum(p[0] for p in pixels) / len(pixels)
                        avg_x = sum(p[1] for p in pixels) / len(pixels)
                        blobs.append({
                            "pixel_count": len(pixels),
                            "mask": blob_mask,
                            "centroid": (round(avg_y, 1), round(avg_x, 1))
                        })

        return blobs

    def _estimate_animal_type(self, pixel_count):
        """
        Rough estimation of animal type based on blob size.
        MLX90640 is 32x24, so sizes are relative.
        """
        if pixel_count > 60:
            return "cow"        # Large warm blob
        elif pixel_count > 25:
            return "dog"        # Medium warm blob
        elif pixel_count > 10:
            return "cat"        # Small warm blob
        else:
            return "unknown"

    def get_frame_stats(self):
        """Get overall thermal frame statistics."""
        thermal_data = self._read_frame()
        if thermal_data is None:
            return None

        return {
            "min_temp": round(float(np.min(thermal_data)), 1),
            "max_temp": round(float(np.max(thermal_data)), 1),
            "avg_temp": round(float(np.mean(thermal_data)), 1),
            "ambient_temp": round(float(np.median(thermal_data)), 1)
        }

    def is_ready(self):
        """Check if thermal camera is ready."""
        return self.mlx is not None


# ─── Standalone test ─────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    from config import ANIMAL_TEMP_MIN, ANIMAL_TEMP_MAX, ANIMAL_BLOB_MIN_PIXELS, THERMAL_REFRESH_RATE

    detector = ThermalDetector(
        temp_min=ANIMAL_TEMP_MIN,
        temp_max=ANIMAL_TEMP_MAX,
        min_blob_pixels=ANIMAL_BLOB_MIN_PIXELS,
        refresh_rate=THERMAL_REFRESH_RATE
    )

    if detector.is_ready():
        print("Scanning thermal... (press Ctrl+C to stop)")
        try:
            while True:
                detections = detector.scan()
                stats = detector.get_frame_stats()
                if stats:
                    print(f"  Frame: min={stats['min_temp']}°C, max={stats['max_temp']}°C, "
                          f"avg={stats['avg_temp']}°C")
                for det in detections:
                    print(f"  🐾 {det['animal_type']}: avg={det['avg_temperature']}°C, "
                          f"pixels={det['warm_pixel_count']}, conf={det['confidence']:.0%}")
                time.sleep(2)
        except KeyboardInterrupt:
            pass
    else:
        print("Thermal camera not available. Check I2C connection.")
