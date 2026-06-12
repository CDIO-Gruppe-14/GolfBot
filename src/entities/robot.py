from dataclasses import dataclass

@dataclass
class Robot:
    x: float = 0.0
    y: float = 0.0
    heading: float = None          # Grader, None hvis kun en markoer
    
    def __repr__(self):
        return f"Robot (Heading={self.heading} ({self.x}, {self.y}))"