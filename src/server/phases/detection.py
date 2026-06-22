"""
GolfBot -- Fase 1 + 7: Detektion
==================================
Finder alle bolde, robot og forhindringer via kamera.
Gemmer positioner i cm-koordinater.

Bruges baade som foerste fase (find alt) og som
fase 7 (tjek om der er flere bolde).
"""

import sys
import os
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.server.helpers.camera_utils import get_fresh_frame, extract_heading
from src.entities.ball import Ball


def _capture_frame(ctx):
    """Tag et frisk billede umiddelbart foer detektion."""
    frame = get_fresh_frame(ctx.camera)
    if frame is None:
        print("[Detektion] FEJL: Kunne ikke tage billede fra kamera")
    return frame


def detect_robot(ctx) -> bool:
    """Find robotten og opdater ctx.robot med position (cm) og heading.

    Returns:
        True ved succes, False hvis billede eller robot ikke kunne findes.
    """
    frame = _capture_frame(ctx)
    if frame is None:
        return False

    robot = ctx.tracker.locate(frame)
    if robot is None:
        print("[Detektion] FEJL: Kunne ikke finde robot paa banen")
        return False

    #Offset for robot height
    from config import CAMERA_HEIGHT_CM, ROBOT_MARKER_HEIGHT_CM

    # Konverter markørens pixel-position til cm på baneplanet
    ctx.robot.x, ctx.robot.y = ctx.field_map.pixel_to_cm(robot.x, robot.y)

    # Korrigér for markørens højde over baneplanet:
    # pixel_to_cm() intersekter strålen med z=0, men markøren sidder på
    # z=ROBOT_MARKER_HEIGHT_CM — det forskyver positionen udad mod kanterne.
    ctx.robot.x, ctx.robot.y = ctx.field_map.correct_height_offset(
        ctx.robot.x, ctx.robot.y,
        camera_height_cm=CAMERA_HEIGHT_CM,
        marker_height_cm=ROBOT_MARKER_HEIGHT_CM,
    )

    ctx.robot.heading = extract_heading(robot, ctx.field_map)

    print(f"[Detektion] {ctx.robot}")
    return True


def detect_balls(ctx) -> Optional[List[Ball]]:
    """Find alle bolde og returner dem som Ball-entiteter i cm-koordinater.

    Returns:
        Liste af Ball (evt. tom), eller None ved kamerafejl.
    """
    frame = _capture_frame(ctx)
    if frame is None:
        return None

    balls = []
    for b in ctx.ball_detector.find_all_balls(frame):
        bx, by = ctx.field_map.pixel_to_cm(b.x, b.y)
        balls.append(Ball(bx, by, b.color))

    print("Fundne bolde:")
    for b in balls:
        print(f"[Detektion] {b}")

    return balls


def detect_obstacles(ctx) -> Optional[List[Tuple[float, float]]]:
    """Find forhindringer (det Roede Kryds) og returner cm-koordinater.

    Returns:
        Liste af (x, y)-tupler (evt. tom), eller None ved kamerafejl.
    """
    frame = _capture_frame(ctx)
    if frame is None:
        return None

    obstacles_cm = []
    for o in ctx.obstacle_detector.find_obstacles(frame):
        ox, oy = ctx.field_map.pixel_to_cm(o.x, o.y)
        obstacles_cm.append((ox, oy))

    if obstacles_cm:
        print(f"[Detektion] Fundet {len(obstacles_cm)} forhindring(er) (Rødt Kryds):")
        for o in obstacles_cm:
            print(f"  - Forhindring på ({o[0]:.1f}, {o[1]:.1f}) cm")

    return obstacles_cm
