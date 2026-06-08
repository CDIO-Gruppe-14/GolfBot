"""
GolfBot -- Kamera-hjaelpefunktioner
=====================================
Funktioner til at tage billeder og finde robot/bolde.
Flyttet fra server/main.py for bedre separation.
"""

import math


def get_fresh_frame(camera, flushes=3):
    """Flusher kameraets buffer og returnerer det nyeste frame."""
    for _ in range(flushes):
        camera.get_frame()
    return camera.get_frame()


def extract_heading(robot, field_map):
    """Beregn heading i cm-koordinater fra dobbelt-markoer.
    Returnerer None hvis kun en markoer er synlig."""
    if robot.back_x is None:
        return None
    fx, fy = field_map.pixel_to_cm(robot.x, robot.y)
    bx, by = field_map.pixel_to_cm(robot.back_x, robot.back_y)
    return math.degrees(math.atan2(fy - by, fx - bx))


def find_robot(camera, tracker, field_map):
    """Tag nyt billede og find robot.
    Returnerer (rx, ry, heading) eller None.
    heading er None hvis kun en markoer er fundet."""
    frame = get_fresh_frame(camera)
    if frame is None:
        return None

    robot = tracker.locate(frame)
    if robot is None:
        return None

    rx, ry = field_map.pixel_to_cm(robot.x, robot.y)
    heading = extract_heading(robot, field_map)
    return (rx, ry, heading)
