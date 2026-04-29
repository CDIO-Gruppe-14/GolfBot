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

# Backends der proeves i raekkefoelge (DirectShow finder oftest eksterne kameraer paa Windows)
_BACKENDS = [
    ("DirectShow", cv2.CAP_DSHOW),
    ("MSMF",       cv2.CAP_MSMF),
    ("Any",        cv2.CAP_ANY),
]


class RobotCamera:
    def __init__(self, camera_index=CAMERA_INDEX):
        self.cap = self._open_camera(camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_FRAME_HEIGHT)
        self.prev_time = 0

    @staticmethod
    def _open_camera(index):
        """Proev flere backends for at finde kameraet (loeser Windows-problemer)."""
        # Proev det angivne index med hver backend
        for name, backend in _BACKENDS:
            cap = cv2.VideoCapture(index, backend)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    print(f"  [Kamera] Aabnet index {index} via {name}")
                    return cap
                cap.release()

        # Fallback: scan index 0-4 med alle backends (maske er indekset forkert)
        for try_idx in range(5):
            if try_idx == index:
                continue
            for name, backend in _BACKENDS:
                cap = cv2.VideoCapture(try_idx, backend)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        print(f"  [Kamera] Fundet paa index {try_idx} via {name} (angivet index {index} virkede ikke)")
                        return cap
                    cap.release()

        # Sidste forsoeeg: standard OpenCV uden backend
        print(f"  [Kamera] ADVARSEL: Proever standard VideoCapture({index}) som fallback")
        return cv2.VideoCapture(index)

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
        else:
            print("Intet frame - tjek at kameraet er tilsluttet")
            break
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cam.release()