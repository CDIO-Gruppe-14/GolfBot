import uuid
from dataclasses import dataclass, field

@dataclass
class Ball:
    x: float
    y: float
    color: str
    # Vi bruger en lambda-funktion til at generere en ny streng hver gang
    id_name: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __repr__(self):
        # (Jeg har også tilføjet en manglende parentes til sidst i din streng)
        return f"Ball(id='{self.id_name}' Color='{self.color}' ({self.x}, {self.y}))"