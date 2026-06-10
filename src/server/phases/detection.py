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
from typing import List, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.server.helpers.camera_utils import get_fresh_frame, extract_heading
from src.entities.ball import Ball
from src.entities.robot import Robot

def detect_robot(ctx):
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

    robot = Robot(rx, ry, heading)
    
    print(f"[Detection] {robot}")

    return robot
    
def detect_balls(ctx):
    frame = get_fresh_frame(ctx.camera)
    if frame is None:
        print("[Detektion] FEJL: Kunne ikke tage billede fra kamera")
        return None
    
    # Find alle bolde
    all_balls = ctx.ball_detector.find_all_balls(frame)
    balls = []
    for b in all_balls:
        bx, by = ctx.field_map.pixel_to_cm(b.x, b.y)
        balls.append(Ball(b.color, bx, by, b.color))
        
    print("Fundne bolde:")
    for b in balls:
        print(f"[Detektion] {b}")

    return balls

def detect_obstacals(ctx):
    # Find forhindringer (forberedt til fremtidig implementering)
    # TODO: Brug ObstacleDetector naar den er implementeret
    obstacles_cm = []
    return obstacles_cm