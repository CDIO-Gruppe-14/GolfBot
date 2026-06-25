from dataclasses import dataclass, field
from typing import List, Tuple

@dataclass
class Obstacle:
    """
    A dataclass to hold data for obstacles in the field.
    
    Known obstacles:
    - "red_cross": A red cross placed in the field.
    
    polygon_cm holds the obstacle's actual contour converted to cm coordinates.
    buffered_polygon_cm is the contour expanded by a safety margin, used directly
    for collision detection in pathfinding (point-in-polygon test).
    """
    center_x: float
    center_y: float
    polygon_cm: List[Tuple[float, float]] = field(default_factory=list)
    buffered_polygon_cm: List[Tuple[float, float]] = field(default_factory=list)

    def __repr__(self):
        n = len(self.polygon_cm)
        nb = len(self.buffered_polygon_cm)
        return (f"Obstacle(center=({self.center_x:.1f}, {self.center_y:.1f}), "
                f"polygon={n} pts, buffered={nb} pts)")
