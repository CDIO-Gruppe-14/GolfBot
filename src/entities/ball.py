from dataclasses import dataclass

@dataclass
class Ball:
    def __init__(self, id_name: str, x: int, y: int, color: str):
        self.id_name = id_name
        self.x = x
        self.y = y
        self.color = color

    def __repr__(self):
        return f"Ball (id='{self.id_name}' Color='{self.color}' ({self.x}, {self.y})"