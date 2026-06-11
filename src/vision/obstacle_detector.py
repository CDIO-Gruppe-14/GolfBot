import sys
import os
from dataclasses import dataclass, field

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import FIELD_BORDER_MARGIN_PX, OBSTACLE_MIN_AREA_PX


@dataclass
class ObstaclePosition:
    x: float
    y: float
    area: float = field(default=0.0, repr=False)


class ObstacleDetector:
    """Finder forhindringer (det Røde Kryds) inden for banens indre."""

    def __init__(self, color_detector, field_map, profile="roed",
                 min_area=OBSTACLE_MIN_AREA_PX,
                 border_margin=FIELD_BORDER_MARGIN_PX):
        self.detector = color_detector
        self.field_map = field_map
        self.profile = profile
        self.min_area = min_area
        self.border_margin = border_margin

    def find_obstacles(self, frame) -> list[ObstaclePosition]:
        """Finder alle forhindringer i pixel-koordinater.

        Begrænser detektion til banens indre (Aruco-hjørner, ekskluderer den
        røde bande) og filtrerer små 'røde' prikker fra (støj).
        """
        # Find banens indre (defineret af Aruco-markørerne)
        polygon = self.field_map.field_polygon(margin_px=self.border_margin)

        if self.profile not in self.detector.profiles:
            return []

        obstacles = []
        for r in self.detector.detect_all(frame, self.profile, roi_polygon=polygon):
            if r.found and r.center and r.area > self.min_area:
                obstacles.append(ObstaclePosition(
                    x=r.center[0],
                    y=r.center[1],
                    area=r.area,
                ))
        return obstacles
