from dataclasses import dataclass
from typing import Optional


@dataclass
class RobotPosition:
    x: float  # pixels (front-markør)
    y: float  # pixels (front-markør)
    back_x: Optional[float] = None  # pixels (bag-markør, None hvis ikke fundet)
    back_y: Optional[float] = None  # pixels (bag-markør, None hvis ikke fundet)


class RobotTracker:
    def __init__(self, color_detector, marker_color="green", marker_color_back="blue"):
        self.detector = color_detector
        self.marker_color = marker_color
        self.marker_color_back = marker_color_back

    def locate(self, frame) -> Optional[RobotPosition]:
        """Returnerer RobotPosition(x, y) eller None.

        Hvis to markører er konfigureret og begge findes, inkluderes
        back_x/back_y saa heading kan beregnes i cm-koordinater af serveren.
        """
        # Find front-markør (primaer)
        result_front = self.detector.detect_color(frame, self.marker_color)
        if not result_front.found:
            return None

        pos = RobotPosition(x=result_front.center[0], y=result_front.center[1])

        # Proev at finde bag-markør for direkte heading
        if self.marker_color_back and self.marker_color_back in self.detector.profiles:
            result_back = self.detector.detect_color(frame, self.marker_color_back)
            if result_back.found:
                pos.back_x = result_back.center[0]
                pos.back_y = result_back.center[1]

        return pos
