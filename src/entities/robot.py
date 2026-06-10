from dataclasses import dataclass

@dataclass
class Robot:
    x: float
    y: float
    heading: float          # Grader, None hvis kun en markoer
    
    def __repr__(self):
        return f"Robot (Heading={self.heading} ({self.x}, {self.y}))"