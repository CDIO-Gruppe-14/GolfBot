from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class Obstacle:
    """
    A dataclass to hold data for obstacles in the field.
    
    Known obstacles:
    - "red_cross": A red cross placed in the field.
    
    The properties dictionary can be used to store extra data
    for future obstacle types without breaking the base structure.
    """
    x: int
    y: int
    radius: float #sikkerhedszone rundt om

    def __repr__(self):
        return f"Obstacle (Sikkerhedszone: {self.radius} ({self.x},{self.y}))"
