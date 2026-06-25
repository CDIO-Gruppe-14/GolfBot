import cv2
import numpy as np
import math

class ArucoDetector:
    """Wrapper for ArUco marker detection."""
    
    def __init__(self, dictionary_id=cv2.aruco.DICT_4X4_50):
        self.dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id)
        self.parameters = cv2.aruco.DetectorParameters()
        # For newer OpenCV versions (4.7+), use ArucoDetector. For older, fallback to detectMarkers.
        if hasattr(cv2.aruco, 'ArucoDetector'):
            self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.parameters)
        else:
            self.detector = None
    
    def detect(self, frame) -> dict[int, np.ndarray]:
        """Detektér alle markører. Returnerer {id: corners[4×2]}."""
        if self.detector:
            corners, ids, _ = self.detector.detectMarkers(frame)
        else:
            corners, ids, _ = cv2.aruco.detectMarkers(frame, self.dictionary, parameters=self.parameters)
            
        if ids is None:
            return {}
        return {int(ids[i][0]): corners[i][0] for i in range(len(ids))}
    
    def get_center(self, corners) -> tuple[float, float]:
        """Beregn center fra 4 hjørner."""
        return float(corners[:, 0].mean()), float(corners[:, 1].mean())
    
    def get_heading_deg(self, corners, rotation_offset=0) -> float:
        """Beregn heading (grader) fra markørens orientering.
        Top-left→top-right vektor = markørens 'højre'-retning.
        rotation_offset kompenserer for fysisk skæv montering."""
        tl, tr = corners[0], corners[1]
        dx, dy = tr[0] - tl[0], tr[1] - tl[1]
        raw = math.degrees(math.atan2(dy, dx))
        return (raw + rotation_offset + 180) % 360 - 180
