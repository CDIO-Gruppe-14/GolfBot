import cv2
import numpy as np
import json
import os
from dataclasses import dataclass
from typing import Optional

PROFILES_DIR = "color_profiles"


@dataclass
class DetectionResult:
    """Resultatet fra en farvedetektion."""
    found:   bool
    center:  Optional[tuple]  = None  # (x, y) i pixels
    area:    float            = 0.0   # Areal i pixels²
    contour: Optional[object] = None  # Rå OpenCV kontur
    mask:    Optional[object] = None  # Binær maske (debug)
    bbox:    Optional[tuple]  = None  # (x, y, w, h)


class ColorDetector:
    def __init__(self, min_area: int = 300):
        self.profiles: dict[str, dict] = {}
        self.min_area = min_area

    # ── Profil-håndtering ─────────────────────────────────────

    def load_profile(self, name: str) -> bool:
        path = os.path.join(PROFILES_DIR, f"{name}.json")
        if not os.path.exists(path):
            print(f"  [ColorDetector] Profil ikke fundet: {path}")
            print(f"  Kør først: python src/vision/color_calibrator.py {name}")
            return False
        with open(path) as f:
            self.profiles[name] = json.load(f)
        print(f"  [ColorDetector] Profil indlæst: '{name}'")
        return True

    def set_profile_manual(self, name: str, lower: list, upper: list):
        self.profiles[name] = {"name": name, "lower": lower, "upper": upper}

    # ── Hoved-detektion ───────────────────────────────────────

    def detect_color(self, frame, profile_name: str,
                     debug: bool = False) -> DetectionResult:
        if profile_name not in self.profiles:
            print(f"  [ColorDetector] Profil '{profile_name}' ikke indlæst.")
            return DetectionResult(found=False)

        profile = self.profiles[profile_name]
        lower = np.array(profile["lower"], dtype=np.uint8)
        upper = np.array(profile["upper"], dtype=np.uint8)

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)

        # Hue wraparound for rød (profilen gemmer kun ét range)
        h_center = profile.get("h")
        h_tol = profile.get("h_tol")
        if h_center is not None and h_tol is not None:
            if h_center - h_tol < 0:
                lower2 = np.array([h_center - h_tol + 180,
                                   profile["lower"][1], profile["lower"][2]])
                upper2 = np.array([179, profile["upper"][1], profile["upper"][2]])
                mask |= cv2.inRange(hsv, lower2, upper2)
            if h_center + h_tol > 179:
                lower2 = np.array([0, profile["lower"][1], profile["lower"][2]])
                upper2 = np.array([h_center + h_tol - 180,
                                   profile["upper"][1], profile["upper"][2]])
                mask |= cv2.inRange(hsv, lower2, upper2)

        # Morfologi — fjern støj og luk huller
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

        x, y, w, h = cv2.boundingRect(best)

        if debug:
            self._show_debug(frame, mask, best, (cx, cy), profile_name)

        return DetectionResult(
            found=True,
            center=(cx, cy),
            area=area,
            contour=best,
            mask=mask,
            bbox=(x, y, w, h),
        )

    # ── Navngivne hjælpere ────────────────────────────────────

    def detect_yellow(self, frame, debug=False) -> DetectionResult:
        return self.detect_color(frame, "yellow", debug=debug)

    def detect_green(self, frame, debug=False) -> DetectionResult:
        return self.detect_color(frame, "green", debug=debug)

    def detect_orange(self, frame, debug=False) -> DetectionResult:
        return self.detect_color(frame, "orange", debug=debug)

    def detect_blue(self, frame, debug=False) -> DetectionResult:
        return self.detect_color(frame, "blue", debug=debug)

    # ── Debug / tegning ───────────────────────────────────────

    def _show_debug(self, frame, mask, contour, center, name):
        debug_frame = frame.copy()
        cv2.drawContours(debug_frame, [contour], -1, (0, 255, 0), 2)
        cv2.circle(debug_frame, center, 8, (0, 0, 255), -1)
        cv2.putText(debug_frame, f"[{name}] center: {center}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        cv2.imshow(f"Debug: {name}", debug_frame)
        cv2.imshow(f"Maske: {name}", mask)
        cv2.waitKey(1)

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


# ─────────────────────────────────────────────────────────────
#  Live test:  python src/vision/color_detector.py yellow
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    from camera import RobotCamera

    profile = sys.argv[1] if len(sys.argv) > 1 else "default"

    detector = ColorDetector(min_area=500)
    if not detector.load_profile(profile):
        print("Kalibrér farven først:")
        print(f"  python src/vision/color_calibrator.py {profile}")
        exit(1)

    camera = RobotCamera()
    print(f"\nDetekterer '{profile}' — tryk 'q' for at afslutte\n")

    while True:
        frame = camera.get_frame()
        if frame is None:
            continue

        result = detector.detect_color(frame, profile)

        if result.found:
            print(f"  FUNDET  center={result.center}  areal={result.area:.0f}px²")
        else:
            print("  Ikke fundet")

        annotated = detector.draw_detection(frame, result, label=profile)
        cv2.imshow("ColorDetector", annotated)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    camera.release()
