import cv2
import numpy as np
import json
from dataclasses import dataclass
from typing import Optional
import os
import math

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

    def load_all_profiles(self) -> list[str]:
        """Indlæs alle .json profiler fra color_profiles/. Returnerer liste af indlæste navne."""
        loaded = []
        if not os.path.isdir(PROFILES_DIR):
            return loaded
        for filename in os.listdir(PROFILES_DIR):
            if filename.endswith(".json"):
                name = filename[:-5]
                if self.load_profile(name):
                    loaded.append(name)
        return loaded

    def set_profile_manual(self, name: str, lower: list, upper: list):
        self.profiles[name] = {"name": name, "lower": lower, "upper": upper}

    def _build_mask(self, hsv_frame, profile):
        """Byg HSV-maske fra en profil. Forventer allerede konverteret HSV-frame."""
        h, s, v = profile.get("h"), profile.get("s"), profile.get("v")
        h_tol, s_tol, v_tol = profile.get("h_tol"), profile.get("s_tol"), profile.get("v_tol")

        if all(x is not None for x in (h, s, v, h_tol, s_tol, v_tol)):
            return build_hsv_mask(hsv_frame, h, s, v, h_tol, s_tol, v_tol)

        lower = np.array(profile["lower"], dtype=np.uint8)
        upper = np.array(profile["upper"], dtype=np.uint8)
        mask = cv2.inRange(hsv_frame, lower, upper)
        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    def _contours_to_results(self, contours, mask) -> list[DetectionResult]:
        """Konvertér konturer til en liste af DetectionResult (filtreret på min_area)."""
        results = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area:
                continue
            M = cv2.moments(cnt)
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            x, y, w, h_box = cv2.boundingRect(cnt)
            results.append(DetectionResult(
                found=True, center=(cx, cy), area=area,
                contour=cnt, mask=mask, bbox=(x, y, w, h_box),
            ))
        return results

    def detect_color(self, frame, profile_name: str) -> DetectionResult:
        """Returnér den største detektion for én farve."""
        results = self.detect_all(frame, profile_name)
        if not results:
            return DetectionResult(found=False)
        return max(results, key=lambda r: r.area)

    def detect_all(self, frame, profile_name: str, _hsv=None) -> list[DetectionResult]:
        """Returnér alle detektioner for én farve (sorteret størst først)."""
        if profile_name not in self.profiles:
            raise ValueError(f"Profil '{profile_name}' ikke indlæst — kald load_profile() først.")

        hsv = _hsv if _hsv is not None else cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = self._build_mask(hsv, self.profiles[profile_name])
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        results = self._contours_to_results(contours, mask)
        results.sort(key=lambda r: r.area, reverse=True)
        return results

    def detect_all_colors(self, frame) -> dict[str, list[DetectionResult]]:
        """Kør detektion for alle indlæste profiler. Returnér {farvenavn: [resultater]}."""
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return {name: self.detect_all(frame, name, _hsv=hsv) for name in self.profiles}


def draw_detection(frame, result: DetectionResult,
                   label: str = "", color: tuple = (0, 255, 0)):
    """Tegn én detektion på frame. Returnerer kopi med annotation."""
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

    DRAW_COLORS = [
        (0, 255, 0), (255, 0, 0), (0, 0, 255),
        (255, 255, 0), (0, 255, 255), (255, 0, 255),
    ]

    detector = ColorDetector(min_area=500)

    # Hvis et profil-navn angives som argument, brug kun det — ellers indlæs alle
    if len(sys.argv) > 1:
        profile_filter = sys.argv[1]
        if not detector.load_profile(profile_filter):
            exit(1)
        loaded = [profile_filter]
    else:
        loaded = detector.load_all_profiles()
        if not loaded:
            print("Ingen profiler fundet. Kalibrér først:")
            print("  python src/vision/color_calibrator.py <farvenavn>")
            exit(1)

    print(f"\nIndlæste profiler: {loaded}")
    print("Tryk 'q' for at afslutte\n")

    camera = RobotCamera()
    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                continue

            all_results = detector.detect_all_colors(frame)
            annotated = frame.copy()

            for i, (name, results) in enumerate(all_results.items()):
                draw_color = DRAW_COLORS[i % len(DRAW_COLORS)]
                for r in results:
                    annotated = draw_detection(annotated, r, label=name, color=draw_color)
                    print(f"  {name}: center={r.center}  areal={r.area:.0f}px²")

            cv2.imshow("ColorDetector", annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        camera.release()


#finder objekt med størst farve dedektion fx rødt kors er den røde farve tydeligere/bonger mere ud end rødlig bordplade fx.
def get_largest_result(results: list[DetectionResult]) -> Optional[DetectionResult]:
    if not results:
        return None
    return max(results, key=lambda r: r.area)

# Beregner afstand i cm mellem robot og forhindring baseret på deres detektionscentre i pixels og en kalibreret cm-per-pixel faktor.
def distance_px(p1: tuple[int, int], p2: tuple[int, int]) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

# Estimerer afstand i cm mellem robot og forhindring. Returnerer None hvis det ikke er muligt (fx ingen detektion).
def estimate_obstacle_distance_cm(
    robot_result: Optional[DetectionResult],
    obstacle_result: Optional[DetectionResult],
    cm_per_pixel: float
) -> Optional[float]:
    if not robot_result or not obstacle_result:
        return None
    if not robot_result.center or not obstacle_result.center:
        return None

    d_px = distance_px(robot_result.center, obstacle_result.center)
    return d_px * cm_per_pixel