import cv2
import json
import numpy as np
import os

CALIBRATION_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "calibration", "field_corners.json"
)

# Bruges til at beregne kameraets nadir (punkt på banen direkte under kameraet)
from config import CAMERA_FRAME_WIDTH, CAMERA_FRAME_HEIGHT


class FieldMap:
    def __init__(self, field_corners_px=None, field_size_cm=None, aruco_detector=None):
        """
        field_corners_px: de 4 hjørner af banen i pixelkoordinater
        [(øverst-venstre), (øverst-højre), (nederst-højre), (nederst-venstre)]

        Prioritet for hjørner:
          1. field_corners_px argumentet (hvis angivet direkte)
          2. calibration/field_corners.json (gemt med field_calibrator.py)
          3. FIELD_CORNERS_PX fra config.py (fallback-værdier)

        field_size_cm hentes fra config.py's FIELD_SIZE_CM hvis ikke angivet.
        """
        from config import FIELD_SIZE_CM, FIELD_CORNERS_PX

        if field_size_cm is None:
            field_size_cm = FIELD_SIZE_CM
            
        self.field_size_cm = field_size_cm
        self.aruco = aruco_detector

        if field_corners_px is None:
            field_corners_px = self._load_corners(fallback=FIELD_CORNERS_PX)

        self.corners = field_corners_px
        self.M = self._compute_transform(field_corners_px, field_size_cm)
        
    def field_polygon(self, margin_px: int = 0) -> list[tuple[float, float]]:
        """De 4 banehjørner (Aruco) som polygon, evt. krympet 'margin_px' indad mod centrum.

        Bruges som ROI til bold- og forhindringsdetektion, så detektion begrænses til
        banens indre (defineret af Aruco-markørerne) og den røde bande udelukkes.
        """
        if not self.corners:
            return []
        if margin_px <= 0:
            return [tuple(c) for c in self.corners]
        cx = sum(c[0] for c in self.corners) / len(self.corners)
        cy = sum(c[1] for c in self.corners) / len(self.corners)
        shrunk = []
        for x, y in self.corners:
            dx, dy = cx - x, cy - y
            dist = (dx * dx + dy * dy) ** 0.5 or 1.0
            shrunk.append((x + dx / dist * margin_px, y + dy / dist * margin_px))
        return shrunk

    def calibrate_from_aruco(self, frame) -> bool:
        """Find 4 hjørne-markører og beregn perspektiv-transformation."""
        if not self.aruco:
            return False
            
        from config import FIELD_MARKER_IDS
        detections = self.aruco.detect(frame)
        
        corner_ids = FIELD_MARKER_IDS  # [0, 1, 2, 3] fra config
        found = [corner_ids[i] in detections for i in range(4)]
        
        if not all(found):
            missing = [corner_ids[i] for i in range(4) if not found[i]]
            print(f"Mangler bane-markører: {missing}")
            return False
        
        corners_px = [self.aruco.get_center(detections[cid]) 
                      for cid in corner_ids]
        self.corners = corners_px
        self.M = self._compute_transform(corners_px, self.field_size_cm)
        return True

    @staticmethod
    def _load_corners(fallback) -> list:
        """
        Prøver at indlæse hjørner fra calibration/field_corners.json.
        Falder tilbage til config.py's FIELD_CORNERS_PX hvis filen ikke findes.
        """
        if os.path.exists(CALIBRATION_FILE):
            with open(CALIBRATION_FILE) as f:
                data = json.load(f)
            corners = [tuple(c) for c in data["corners"]]
            print(f"  [FieldMap] Hjørner indlæst fra kalibrering: {CALIBRATION_FILE}")
            return corners

        print(f"  [FieldMap] Ingen kalibrering fundet — bruger fallback fra config.py")
        print(f"             Kør 'python src/vision/field_calibrator.py' for præcis kalibrering")
        return fallback

    def _compute_transform(self, corners_px, size_cm):
        src = np.float32(corners_px)
        dst = np.float32([
            [0, 0], [size_cm[0], 0],
            [size_cm[0], size_cm[1]], [0, size_cm[1]]
        ])
        return cv2.getPerspectiveTransform(src, dst)

    def pixel_to_cm(self, px, py) -> tuple[float, float]:
        """Konverterer pixel-koordinat til (x_cm, y_cm)."""
        pt = np.float32([[[px, py]]])
        result = cv2.perspectiveTransform(pt, self.M)
        return float(result[0][0][0]), float(result[0][0][1])

    def cm_to_pixel(self, x_cm, y_cm) -> tuple[float, float]:
        """Konverterer cm-koordinat tilbage til pixel (invers af pixel_to_cm).
        Bruges til at tegne cm-baserede ruter oven paa kamerabilledet."""
        Minv = np.linalg.inv(self.M)
        pt = np.float32([[[x_cm, y_cm]]])
        result = cv2.perspectiveTransform(pt, Minv)
        return float(result[0][0][0]), float(result[0][0][1])

    @property
    def _nadir_cm(self) -> tuple[float, float]:
        """Beregner (lazy) cm-positionen direkte under kameraet (nadir-punktet).

        Estimeres som midten af frame'et konverteret via den eksisterende homografi.
        Resultatet caches efter foerste kald.
        """
        if not hasattr(self, '_nadir_cm_cache'):
            self._nadir_cm_cache = self.pixel_to_cm(
                CAMERA_FRAME_WIDTH / 2.0,
                CAMERA_FRAME_HEIGHT / 2.0,
            )
        return self._nadir_cm_cache

    def correct_height_offset(
        self,
        x_cm: float,
        y_cm: float,
        camera_height_cm: float,
        marker_height_cm: float,
    ) -> tuple[float, float]:
        """Korrigerer for at ArUco-markøren sidder hævet over baneoverfladen.

        pixel_to_cm() projicerer markør-pixlen ned paa z=0-planet (baneplanet),
        men markøren er i virkeligheden paa hoejde marker_height_cm. Det bevirker
        at den beregnede position forskydes udad fra kameraets nadir -- fejlen
        vokser jo laengere robotten er fra midten af billedet.

        Korrektionen traekkker resultatet mod nadir med faktoren h/H:
            x_ground = x_homo + (x_nadir - x_homo) * (marker_height_cm / camera_height_cm)

        Args:
            x_cm, y_cm:          Ukorrigeret cm-position fra pixel_to_cm().
            camera_height_cm:    Kameraets hoejde over baneoverfladen (cm).
            marker_height_cm:    Markørens hoejde over baneoverfladen (cm).

        Returns:
            (x_ground_cm, y_ground_cm) -- korrigeret position paa baneplanet.
        """
        scale = marker_height_cm / camera_height_cm
        nx, ny = self._nadir_cm
        corrected_x = x_cm + (nx - x_cm) * scale
        corrected_y = y_cm + (ny - y_cm) * scale
        return corrected_x, corrected_y
