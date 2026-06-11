from dataclasses import dataclass

@dataclass
class Ball:
    id_name: str
    x: float
    y: float
    color: str

    def __repr__(self):
        return f"Ball (id='{self.id_name}' Color='{self.color}' ({self.x}, {self.y})"