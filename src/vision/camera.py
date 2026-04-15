import cv2
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import CAMERA_INDEX, CAMERA_FRAME_WIDTH, CAMERA_FRAME_HEIGHT

# For at kunne launche kameraet skal man køre disse to kommandoer i terminalen:
# pip install -r requirements.txt
# pip install opencv-python numpy
# Test af kameraet ved at køre filen: python src/vision/camera.py
# Tryk 'q' for at lukke kameraet ned

class RobotCamera:
    def __init__(self, camera_index=CAMERA_INDEX):
        self.cap = cv2.VideoCapture(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_FRAME_HEIGHT)
        self.prev_time = 0

    def get_frame(self):
        ret, frame = self.cap.read()
        return frame if ret else None

    def get_fps(self):
        """Beregner Frames Per Second."""
        new_time = time.time()
        fps = 1 / (new_time - self.prev_time)
        self.prev_time = new_time
        return int(fps)

    def release(self):
        self.cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    cam = RobotCamera()
    while True:
        frame = cam.get_frame()
        if frame is not None:
            fps = cam.get_fps()
            cv2.putText(frame, f"FPS: {fps}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            cv2.imshow('GolfBot Vision Debug', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cam.release()