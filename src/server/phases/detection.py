"""
GolfBot -- Fase 1 + 7: Detektion
==================================
Finder alle bolde, robot og forhindringer via kamera.
Gemmer positioner i cm-koordinater.

Her udfores kalibrering og der laves et billede af
hvor boldene ligger i koordinatsystemet.

Bruges baade som foerste fase (find alt) og som
fase 7 (tjek om der er flere bolde).
"""

import sys
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.server.helpers.camera_utils import get_fresh_frame, extract_heading


@dataclass
class DetectionResult:
    """Resultat af en fuld detektion af banen."""
    robot_x: float
    robot_y: float
    robot_heading: float          # Grader (altid tilgængelig via ArUco)
    balls: list                   # Liste af (x_cm, y_cm, color) tupler
    obstacles: list               # Liste af (x_cm, y_cm, radius_cm) -- forberedt til A*

    def has_balls(self):
        """Returnerer True hvis der er bolde paa banen."""
        return len(self.balls) > 0


def detect_all(ctx):
    """
    Fase 1+7: Tag billede, find alle elementer, gem positioner.

    Udforer kalibrering og laver et overblik over hvor boldene
    ligger i koordinatsystemet.

    Args:
        ctx: GameContext med kamera og vision-moduler

    Returns:
        DetectionResult eller None hvis robot ikke kan findes.
    """
    frame = get_fresh_frame(ctx.camera)
    if frame is None:
        print("[Detektion] FEJL: Kunne ikke tage billede fra kamera")
        return None

    # Find robot
    robot = ctx.tracker.locate(frame)
    if robot is None:
        print("[Detektion] FEJL: Kunne ikke finde robot paa banen")
        return None

    rx, ry = ctx.field_map.pixel_to_cm(robot.x, robot.y)
    heading = extract_heading(robot, ctx.field_map)

    # Opdater heading i context
    ctx.estimated_heading = heading

    # Find alle bolde
    all_balls = ctx.ball_detector.find_all_balls(frame)
    balls_cm = []
    for b in all_balls:
        bx, by = ctx.field_map.pixel_to_cm(b.x, b.y)
        balls_cm.append((bx, by, b.color))

    # Find forhindringer (forberedt til fremtidig implementering)
    # TODO: Brug ObstacleDetector naar den er implementeret
    obstacles_cm = []

    print("[Detektion] Robot: ({:.1f}, {:.1f})  Heading: {:.1f}".format(
        rx, ry, heading))
    print("[Detektion] Fandt {} bolde, {} forhindringer".format(
        len(balls_cm), len(obstacles_cm)))
    for i, (bx, by, color) in enumerate(balls_cm):
        print("  Bold {}: ({:.1f}, {:.1f}) - {}".format(i + 1, bx, by, color))

    return DetectionResult(
        robot_x=rx,
        robot_y=ry,
        robot_heading=heading,
        balls=balls_cm,
        obstacles=obstacles_cm
    )
