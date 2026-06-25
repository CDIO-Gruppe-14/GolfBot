import cv2
import math
import numpy as np
import json
from dataclasses import dataclass
from typing import Optional
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import COLOR_MIN_AREA, MORPH_KERNEL_SIZE, MIN_CIRCULARITY, MAX_ASPECT_RATIO

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
    def __init__(self, min_area: int = COLOR_MIN_AREA):
        self.profiles: dict[str, dict] = {}
        self.min_area = min_area
        self._missing_warned: set[str] = set()

    def load_profile(self, name: str) -> bool:
        path = os.path.join(PROFILES_DIR, f"{name}.json")
        if not os.path.exists(path):
            if name not in self._missing_warned:
                print(f"  [ColorDetector] Profil ikke fundet: {path}")
                print(f"  Kør først: python src/vision/color_calibrator.py {name}")
                self._missing_warned.add(name)
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
        kernel = np.ones((MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        return mask

    def _contours_to_results(self, contours, mask,
                             profile: dict | None = None,
                             offset: tuple = (0, 0)) -> list[DetectionResult]:
        """Konvertér konturer til en liste af DetectionResult (filtreret på areal).

        Args:
            profile: Farveprofil-dict med valgfri 'min_area'/'max_area' felter.
            offset:  (ox, oy) der lægges til koordinater (brugt ved ROI-crop).
        """
        min_a = profile.get("min_area", self.min_area) if profile else self.min_area
        max_a = profile.get("max_area") if profile else None
        # Formfilter (default fra config) — en profil kan opte ud med null
        min_circ = profile.get("min_circularity", MIN_CIRCULARITY) if profile else MIN_CIRCULARITY
        max_ar = profile.get("max_aspect_ratio", MAX_ASPECT_RATIO) if profile else MAX_ASPECT_RATIO
        ox, oy = offset

        results = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < min_a:
                continue
            if max_a is not None and area > max_a:
                continue
            x, y, w, h_box = cv2.boundingRect(cnt)
            # Frasortér ikke-runde konturer (fx rektangulære LEGO-klodser)
            if min_circ is not None or max_ar is not None:
                perimeter = cv2.arcLength(cnt, True)
                if perimeter == 0:
                    continue
                if min_circ is not None:
                    circularity = 4 * math.pi * area / (perimeter * perimeter)
                    if circularity < min_circ:
                        continue
                if max_ar is not None:
                    if w == 0 or h_box == 0:
                        continue
                    if max(w / h_box, h_box / w) > max_ar:
                        continue
            M = cv2.moments(cnt)
            if M["m00"] == 0:
                continue
            cx = int(M["m10"] / M["m00"]) + ox
            cy = int(M["m01"] / M["m00"]) + oy
            
            global_cnt = cnt + np.array([ox, oy]) if (ox != 0 or oy != 0) else cnt
            
            results.append(DetectionResult(
                found=True, center=(cx, cy), area=area,
                contour=global_cnt, mask=mask, bbox=(x + ox, y + oy, w, h_box),
            ))
        return results

    def detect_color(self, frame, profile_name: str) -> DetectionResult:
        """Returnér den største detektion for én farve."""
        results = self.detect_all(frame, profile_name)
        if not results:
            return DetectionResult(found=False)
        return max(results, key=lambda r: r.area)

    def detect_all(self, frame, profile_name: str, _hsv=None,
                   roi: tuple | None = None,
                   roi_polygon: list | None = None) -> list[DetectionResult]:
        """Returnér alle detektioner for én farve (sorteret størst først).

        Args:
            roi: (x, y, w, h) — begræns detektion til dette rektangel.
                 Returnerede koordinater er i fuld-frame-space.
            roi_polygon: liste af hjørnepunkter (fx de 4 Aruco-banehjørner) —
                 begræns detektion til pixels INDE i polygonet. Croppes til
                 polygonets bounding box og maskeres med selve polygonet, så
                 fx den røde bande udenfor udelukkes. Tager forrang over 'roi'.
        """
        if profile_name not in self.profiles:
            raise ValueError(f"Profil '{profile_name}' ikke indlæst — kald load_profile() først.")

        profile = self.profiles[profile_name]
        offset = (0, 0)
        poly_mask = None

        if roi_polygon:
            pts = np.array(roi_polygon, dtype=np.int32)
            rx, ry, rw, rh = cv2.boundingRect(pts)
            frame = frame[ry:ry+rh, rx:rx+rw]
            _hsv = None  # force recompute on cropped frame
            offset = (rx, ry)
            # Polygon-maske i crop-koordinater (udelukker alt udenfor banen)
            poly_mask = np.zeros((rh, rw), dtype=np.uint8)
            cv2.fillConvexPoly(poly_mask, pts - (rx, ry), 255)
        elif roi is not None:
            rx, ry, rw, rh = roi
            frame = frame[ry:ry+rh, rx:rx+rw]
            _hsv = None  # force recompute on cropped frame
            offset = (rx, ry)

        if frame is None or frame.size == 0:
            return []

        hsv = _hsv if _hsv is not None else cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = self._build_mask(hsv, profile)
        if poly_mask is not None:
            mask = cv2.bitwise_and(mask, poly_mask)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
        results = self._contours_to_results(contours, mask, profile=profile, offset=offset)
        results.sort(key=lambda r: r.area, reverse=True)
        return results

    def detect_all_colors(self, frame,
                          roi: tuple | None = None) -> dict[str, list[DetectionResult]]:
        """Kør detektion for alle indlæste profiler. Returnér {farvenavn: [resultater]}.

        Args:
            roi: (x, y, w, h) — begræns detektion til dette rektangel.
        """
        # Når ROI bruges, kan vi ikke dele HSV-frame på tværs af profiler
        if roi is not None:
            return {name: self.detect_all(frame, name, roi=roi)
                    for name in self.profiles}
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return {name: self.detect_all(frame, name, _hsv=hsv) for name in self.profiles}


def draw_detection(frame, result: DetectionResult,
                   label: str = "", color: tuple = (0, 255, 0)):
    """Tegn én detektion på frame. Returnerer kopi med annotation."""
    out = frame.copy()
    if not result.found:
        return out
    if result.contour is not None:
        cv2.drawContours(out, [result.contour], -1, color, 2)
    elif result.bbox:
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
    from aruco_detector import ArucoDetector
    from config import ARUCO_DICT, ROBOT_MARKER_ID, FIELD_MARKER_IDS, FIELD_CORNERS_PX

    DRAW_COLORS = [
        (0, 255, 0), (255, 0, 0), (0, 0, 255),
        (255, 255, 0), (0, 255, 255), (255, 0, 255),
    ]

    detector = ColorDetector()

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

    # Initialiser ArUco Detector
    aruco = ArucoDetector(ARUCO_DICT)

    # Indlæs banens hjørner til tegning (hvis de findes)
    CALIBRATION_FILE = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "calibration", "field_corners.json"
    )
    corners_loaded = []
    if os.path.exists(CALIBRATION_FILE):
        try:
            with open(CALIBRATION_FILE) as f:
                corners_loaded = json.load(f).get("corners", [])
            print(f"Indlæste banens hjørner fra {CALIBRATION_FILE}")
        except Exception as e:
            print(f"Fejl ved indlæsning af field_corners.json: {e}")

    camera = RobotCamera()
    last_live_corners = None
    try:
        while True:
            frame = camera.get_frame()
            if frame is None:
                continue

            annotated = frame.copy()

            # Detektér ArUco-markører live
            detections = aruco.detect(frame)

            # 1. Tegn banekanter (Prioritet: 1. Live ArUco, 2. Last known live, 3. Gemt JSON, 4. Config fallback)
            live_corners = []
            found_all_live = True
            for cid in FIELD_MARKER_IDS:
                if cid in detections:
                    live_corners.append(aruco.get_center(detections[cid]))
                else:
                    found_all_live = False

            if found_all_live:
                # Gem til memory
                last_live_corners = live_corners
                # Tegn med en tyk grøn linje
                pts = np.array(live_corners, dtype=np.int32)
                cv2.polylines(annotated, [pts], isClosed=True, color=(0, 255, 0), thickness=3)
                for idx, pt in enumerate(live_corners):
                    cv2.circle(annotated, (int(pt[0]), int(pt[1])), 8, (0, 255, 0), -1)
                    cv2.putText(annotated, f"Live Hjoerne {idx}", (int(pt[0]) + 10, int(pt[1]) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            elif last_live_corners is not None:
                # Brug seneste kendte live-position (lidt mørkere grøn for at vise det er fra hukommelsen)
                pts = np.array(last_live_corners, dtype=np.int32)
                cv2.polylines(annotated, [pts], isClosed=True, color=(0, 180, 0), thickness=2)
                for idx, pt in enumerate(last_live_corners):
                    cv2.circle(annotated, (int(pt[0]), int(pt[1])), 6, (0, 180, 0), -1)
                    cv2.putText(annotated, f"Live Hjoerne {idx} (memory)", (int(pt[0]) + 10, int(pt[1]) - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 180, 0), 1)
            elif corners_loaded and len(corners_loaded) == 4:
                # Hvis vi har gemte hjørner: Tegn med orange linje
                pts = np.array(corners_loaded, dtype=np.int32)
                cv2.polylines(annotated, [pts], isClosed=True, color=(255, 100, 0), thickness=2)
                for idx, pt in enumerate(corners_loaded):
                    pt_int = (int(pt[0]), int(pt[1]))
                    cv2.circle(annotated, pt_int, 6, (255, 100, 0), -1)
                    cv2.putText(annotated, f"Hjoerne {idx} (gemt)", (pt_int[0] + 8, pt_int[1] - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 100, 0), 1)
            else:
                # Fallback fra config.py: Tegn med tynd blå linje
                pts = np.array(FIELD_CORNERS_PX, dtype=np.int32)
                cv2.polylines(annotated, [pts], isClosed=True, color=(255, 0, 0), thickness=1)
                for idx, pt in enumerate(FIELD_CORNERS_PX):
                    pt_int = (int(pt[0]), int(pt[1]))
                    cv2.circle(annotated, pt_int, 4, (255, 0, 0), -1)
                    cv2.putText(annotated, f"Hjoerne {idx} (fallback)", (pt_int[0] + 8, pt_int[1] - 8),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)

            # 2. Tegn alle detekterede ArUco-markører live
            for cid, corners in detections.items():
                pts = corners.astype(np.int32)
                # Banemarkører tegnes grønne, andre lilla
                color = (0, 255, 0) if cid in FIELD_MARKER_IDS else (255, 0, 255)
                cv2.polylines(annotated, [pts], isClosed=True, color=color, thickness=2)
                
                center = aruco.get_center(corners)
                label = f"ID {cid}"
                if cid == ROBOT_MARKER_ID:
                    # Beregn og tegn robottens retning (heading)
                    heading = aruco.get_heading_deg(corners)
                    label = f"Robot ID {cid} ({heading:.1f} deg)"
                    # Tegn retningspil
                    tl, tr = corners[0], corners[1]
                    front_mid = ((tl[0] + tr[0]) / 2, (tl[1] + tr[1]) / 2)
                    cv2.arrowedLine(annotated, (int(center[0]), int(center[1])), 
                                    (int(front_mid[0]), int(front_mid[1])), 
                                    (0, 0, 255), 3, tipLength=0.3)
                cv2.putText(annotated, label, (int(center[0]) - 30, int(center[1]) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

            # 3. Vælg banens ROI-polygon (Aruco live → memory → gemt → config-fallback)
            if found_all_live:
                roi_polygon = live_corners
            elif last_live_corners is not None:
                roi_polygon = last_live_corners
            elif corners_loaded and len(corners_loaded) == 4:
                roi_polygon = corners_loaded
            else:
                roi_polygon = FIELD_CORNERS_PX

            # 4. Detektér bolde inden for ROI (Aruco-firkanten)
            ball_profiles = detector.profiles.keys()
            for i, name in enumerate(ball_profiles):
                draw_color = DRAW_COLORS[i % len(DRAW_COLORS)]
                results = detector.detect_all(frame, name, roi_polygon=roi_polygon)
                for r in results:
                    annotated = draw_detection(annotated, r, label=name, color=draw_color)
                    print(f"  {name}: center={r.center}  areal={r.area:.0f}px²")

                # Debug: vis maske for hvid
                if name == "hvid":
                    rx, ry, rw, rh = cv2.boundingRect(np.array(roi_polygon, dtype=np.int32))
                    crop = frame[ry:ry+rh, rx:rx+rw]
                    hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                    mask = detector._build_mask(hsv_crop, detector.profiles["hvid"])
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL,
                                                    cv2.CHAIN_APPROX_SIMPLE)
                    # print(f"  [DEBUG hvid] konturer: {len(contours)}, arealer: {[int(cv2.contourArea(c)) for c in contours[:10]]}")
                    cv2.imshow("Hvid Maske", mask)

                if name == "roed":
                    rx, ry, rw, rh = cv2.boundingRect(np.array(roi_polygon, dtype=np.int32))
                    crop = frame[ry:ry+rh, rx:rx+rw]
                    hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                    mask = detector._build_mask(hsv_crop, detector.profiles["roed"])
                    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                    cv2.imshow("Roed Maske (Forhindring)", mask)
                    print(f"  [DEBUG roed] fandt {len(contours)} konturer. Arealer: {[int(cv2.contourArea(c)) for c in contours[:5]]}")

            cv2.imshow("ColorDetector", annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        camera.release()
