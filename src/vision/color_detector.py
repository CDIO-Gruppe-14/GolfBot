import cv2
import numpy as np
import json
from dataclasses import dataclass
from typing import Optional
import os

from hsv_utils import PROFILES_DIR, build_hsv_mask


@dataclass
class DetectionResult:
    """Resultatet fra en farvedetektion."""
    found:   bool
    center:  Optional[tuple]  = None
    area:    float            = 0.0
    contour: Optional[object] = None
    mask:    Optional[object] = None
    bbox:    Optional[tuple]  = None


class ColorDetector:
    def __init__(self, min_area: int = 300):
        self.profiles: dict[str, dict] = {}
        self.min_area = min_area

    def load_profile(self, name: str) -> bool:
        path = os.path.join(PROFILES_DIR, f"{name}.json")
        if not os.path.exists(path):
            print(f"  [ColorDetector] Profil ikke fundet: {path}")
            print(f"  Kør først: python src/vision/color_calibrator.py {name}")
            return False
        with open(path) as f:
            self.profiles[name] = json.load(f)
        return True

    def set_profile_manual(self, name: str, lower: list, upper: list):
        self.profiles[name] = {"name": name, "lower": lower, "upper": upper}

    def detect_color(self, frame, profile_name: str) -> DetectionResult:
        if profile_name not in self.profiles:
            raise ValueError(f"Profil '{profile_name}' ikke indlæst — kald load_profile() først.")

        profile = self.profiles[profile_name]
        h, s, v = profile.get("h"), profile.get("s"), profile.get("v")
        h_tol, s_tol, v_tol = profile.get("h_tol"), profile.get("s_tol"), profile.get("v_tol")

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        if all(x is not None for x in (h, s, v, h_tol, s_tol, v_tol)):
            mask = build_hsv_mask(hsv, h, s, v, h_tol, s_tol, v_tol)
        else:
            lower = np.array(profile["lower"], dtype=np.uint8)
            upper = np.array(profile["upper"], dtype=np.uint8)
            mask = cv2.inRange(hsv, lower, upper)
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return DetectionResult(found=False, mask=mask)

        best = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(best)

        if area < self.min_area:
            return DetectionResult(found=False, mask=mask)

        M = cv2.moments(best)
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        x, y, w, h_box = cv2.boundingRect(best)

        return DetectionResult(
            found=True, center=(cx, cy), area=area,
            contour=best, mask=mask, bbox=(x, y, w, h_box),
        )

    def draw_detection(self, frame, result: DetectionResult,
                       label: str = "", color: tuple = (0, 255, 0)):
        out = frame.copy()
        if not result.found:
            return out
        if result.bbox:
            x, y, w, h = result.bbox
            cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)
        if result.center:
            cv2.circle(out, result.center, 8, color, -1)
            txt = f"{label} {result.center}" if label else str(result.center)
            cv2.putText(out, txt, (result.center[0] + 10, result.center[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        return out


if __name__ == "__main__":
    import sys
    from camera import RobotCamera

    profile = sys.argv[1] if len(sys.argv) > 1 else "default"

    detector = ColorDetector(min_area=500)
    if not detector.load_profile(profile):
        exit(1)

    camera = RobotCamera()
    print(f"\nDetekterer '{profile}' — tryk 'q' for at afslutte\n")

    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                continue

            result = detector.detect_color(frame, profile)

            if result.found:
                print(f"  FUNDET  center={result.center}  areal={result.area:.0f}px²")

            annotated = detector.draw_detection(frame, result, label=profile)
            cv2.imshow("ColorDetector", annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        camera.release()
