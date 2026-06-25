import math
import sys
import os
from dataclasses import dataclass, field
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import BALL_COLORS, FIELD_BORDER_MARGIN_PX


@dataclass
class BallPosition:
    x: float
    y: float
    color: str   # "orange" eller "white"
    area: float = field(default=0.0, repr=False)


class BallDetector:
    BALL_COLORS = BALL_COLORS  # defineret i config.py

    def __init__(self, color_detector, field_map, border_margin=FIELD_BORDER_MARGIN_PX):
        self.detector = color_detector
        self.field_map = field_map
        self.border_margin = border_margin

    def find_nearest_ball(self, frame, robot_pos=None) -> Optional[BallPosition]:
        """Finder den nærmeste bold (orange foretrækkes). Returnerer None hvis ingen fundet."""
        balls = self.find_all_balls(frame)
        if not balls:
            return None

        # Ingen robotposition — orange foretrækkes, så returnér første (allerede sorteret)
        if robot_pos is None:
            return balls[0]

        # Find den bold der er tættest på robotten
        rx, ry = robot_pos
        return min(balls, key=lambda b: math.hypot(b.x - rx, b.y - ry))

    def find_all_balls(self, frame) -> list[BallPosition]:
        """Finder alle bolde med farve-label (orange/hvid) inden for bane-ROI."""
        # Begræns detektion til banens indre (Aruco-hjørner, ekskluderer den røde bande)
        polygon = self.field_map.field_polygon(margin_px=self.border_margin)

        balls = []

        for color in self.BALL_COLORS:
            if color not in self.detector.profiles:
                continue
            for r in self.detector.detect_all(frame, color, roi_polygon=polygon):
                if r.found and r.center is not None:
                    balls.append(BallPosition(
                        x=r.center[0],
                        y=r.center[1],
                        color=color,
                        area=r.area,
                    ))

        # Orange øverst, derefter størst areal
        balls.sort(key=lambda b: (0 if b.color == "orange" else 1, -b.area))
        return balls
