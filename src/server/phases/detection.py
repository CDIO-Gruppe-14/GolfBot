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
import cv2
import math
import numpy as np
from typing import List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.server.helpers.camera_utils import get_fresh_frame, extract_heading
from src.entities.ball import Ball
from src.entities.obstacals import Obstacle
from src.planning.polygon_utils import buffer_polygon

from config import OBSTACLE_SAFE_RADIUS_CM, ROBOT_RADIUS_CM, OBSTACLE_CONTOUR_SIMPLIFY_CM


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


def _contour_to_cm_polygon(contour, field_map, simplify_epsilon_cm):
    """Konverter en OpenCV pixel-kontur til en forenklet cm-polygon.

    1. Konverter hvert konturpunkt fra pixel til cm via perspektivtransform.
    2. Forenkl polygonen med cv2.approxPolyDP (i cm-rum) for at reducere
       antallet af punkter (~8-12 for et kryds).
    """
    if contour is None or len(contour) == 0:
        return []

    cm_points = []
    for pt in contour:
        px, py = pt[0]  # contour format: Nx1x2
        cx, cy = field_map.pixel_to_cm(float(px), float(py))
        cm_points.append((cx, cy))

    if len(cm_points) < 3:
        return cm_points

    cm_array = np.array(cm_points, dtype=np.float32).reshape(-1, 1, 2)
    simplified = cv2.approxPolyDP(cm_array, simplify_epsilon_cm, closed=True)
    return [(float(pt[0][0]), float(pt[0][1])) for pt in simplified]


def detect_obstacles(ctx) -> Optional[List[Obstacle]]:
    """Find forhindringer (det Roede Kryds) og returner som Obstacle-objekter.

    Hver Obstacle indeholder:
      - center_x, center_y: centroid i cm
      - polygon_cm: forhindringens faktiske form i cm (forenklet kontur)
      - buffered_polygon_cm: formen udvidet med sikkerhedsmargin, klar til
        point-in-polygon kollisionstest i pathfinding

    Returns:
        Liste af Obstacle (evt. tom), eller None ved kamerafejl.
    """
    frame = _capture_frame(ctx)
    if frame is None:
        return None

    margin_cm = OBSTACLE_SAFE_RADIUS_CM + ROBOT_RADIUS_CM

    obstacles = []
    for o in ctx.obstacle_detector.find_obstacles(frame):
        ox, oy = ctx.field_map.pixel_to_cm(o.x, o.y)

        # Konverter pixel-kontur til cm-polygon
        polygon_cm = _contour_to_cm_polygon(
            o.contour, ctx.field_map, OBSTACLE_CONTOUR_SIMPLIFY_CM)

        # Udvid polygonen med sikkerhedsmargin (robot-clearance)
        if polygon_cm and len(polygon_cm) >= 3:
            buffered = buffer_polygon(polygon_cm, margin_cm)
        else:
            # Fallback: ingen kontur tilgaengelig -- brug cirkel-approximation
            n_pts = 12
            buffered = [
                (ox + margin_cm * math.cos(2 * math.pi * i / n_pts),
                 oy + margin_cm * math.sin(2 * math.pi * i / n_pts))
                for i in range(n_pts)
            ]
            polygon_cm = buffered

        obstacle = Obstacle(
            center_x=ox,
            center_y=oy,
            polygon_cm=polygon_cm,
            buffered_polygon_cm=buffered,
        )
        obstacles.append(obstacle)

    if obstacles:
        print(f"[Detektion] Fundet {len(obstacles)} forhindring(er) (Rødt Kryds):")
        for obs in obstacles:
            print(f"  - {obs}")

    return obstacles
