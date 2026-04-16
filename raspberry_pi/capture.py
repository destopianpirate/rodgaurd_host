#from picamera2 import Picamera2
#from time import sleep

#picam2 = Picamera2()
#picam2.start()

#sleep(2)  # allow camera to warm up
#picam2.capture_file("image.jpg")

#print("Image captured!")

from picamera2 import Picamera2
import cv2

picam2 = Picamera2()

config = picam2.create_preview_configuration(
    main={"format": "RGB888"}  # 🔥 important
)
picam2.configure(config)

picam2.start()

while True:
    frame = picam2.capture_array()

    cv2.imshow("Camera", frame)

    if cv2.waitKey(1) == ord('q'):
        break

cv2.destroyAllWindows()
