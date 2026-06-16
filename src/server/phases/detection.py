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

    ctx.robot.x, ctx.robot.y = ctx.field_map.pixel_to_cm(robot.x, robot.y)
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


def detect_obstacles(ctx) -> Optional[List[Tuple[float, float, float]]]:
    """Find forhindringer (det Roede Kryds) og returner cm-koordinater + radius.

    Hver forhindring returneres som (x_cm, y_cm, radius_cm), hvor radius_cm er
    krydsets FYSISKE udstraekning fra centrum -- maalt ud fra bounding-box'en, saa
    pathfinderen kan holde en buffer der svarer til korsets faktiske stoerrelse i
    stedet for at antage et punkt. Falder tilbage til radius 0 hvis bbox mangler.

    Returns:
        Liste af (x, y, radius)-tupler (evt. tom), eller None ved kamerafejl.
    """
    frame = _capture_frame(ctx)
    if frame is None:
        return None

    obstacles_cm = []
    for o in ctx.obstacle_detector.find_obstacles(frame):
        ox, oy = ctx.field_map.pixel_to_cm(o.x, o.y)
        radius = obstacle_radius_cm(ctx.field_map, o, ox, oy)
        obstacles_cm.append((ox, oy, radius))

    if obstacles_cm:
        print(f"[Detektion] Fundet {len(obstacles_cm)} forhindring(er) (Rødt Kryds):")
        for o in obstacles_cm:
            print(f"  - Forhindring på ({o[0]:.1f}, {o[1]:.1f}) cm, radius {o[2]:.1f} cm")

    return obstacles_cm


def obstacle_radius_cm(field_map, obstacle, center_x_cm, center_y_cm) -> float:
    """Maal krydsets fysiske radius (cm) ud fra dets bounding box.

    Krydset er et '+': bbox'ens HJOERNER er tomme (ingen kryds der), saa de ville
    overvurdere udstraekningen (halv diagonal). Den yderste kant er arm-spidserne,
    som ligger i bbox'ens KANT-MIDTPUNKTER. Radius = stoerste afstand fra centrum
    til et kant-midtpunkt = halv arm-bredde (fx 10 cm for et 20 cm kryds).

    Perspektiv-transformen er ikke-lineaer, saa midtpunkterne konverteres til cm
    foer afstanden maales (ingen direkte pixel->cm-skalering). Genbruges af
    route_visualizer, saa plot og koersel maaler krydset ens."""
    bbox = getattr(obstacle, "bbox", None)
    if not bbox:
        return 0.0
    bx, by, bw, bh = bbox
    edge_mids_px = [
        (bx + bw / 2, by),          # top
        (bx + bw / 2, by + bh),     # bund
        (bx, by + bh / 2),          # venstre
        (bx + bw, by + bh / 2),     # hoejre
    ]
    radius = 0.0
    for px, py in edge_mids_px:
        cx, cy = field_map.pixel_to_cm(px, py)
        radius = max(radius, ((cx - center_x_cm) ** 2 + (cy - center_y_cm) ** 2) ** 0.5)
    return radius
