from dataclasses import dataclass
from typing import Optional


@dataclass
class RobotPosition:
    x: float  # pixels
    y: float  # pixels
    # heading_deg fjernet herfra — leveres nu af EV3's gyro via protokollen


class RobotTracker:
    def __init__(self, color_detector, marker_color="green"):
        self.detector = color_detector
        self.marker_color = marker_color

    def locate(self, frame) -> Optional[RobotPosition]:
        """Returnerer RobotPosition(x, y) eller None."""
        result = self.detector.detect_color(frame, self.marker_color)
        if not result.found:
            return None
        return RobotPosition(x=result.center[0], y=result.center[1])
