import cv2
import json
import numpy as np
import os

CALIBRATION_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "calibration", "field_corners.json"
)


class FieldMap:
    def __init__(self, field_corners_px=None, field_size_cm=None):
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

        if field_corners_px is None:
            field_corners_px = self._load_corners(fallback=FIELD_CORNERS_PX)

        self.corners = field_corners_px
        self.M = self._compute_transform(field_corners_px, field_size_cm)

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
