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
    """Heading er nu altid tilgængelig fra ArUco-markøren."""
    # Konvertér pixel-heading til cm-space heading
    # ved at transformere to punkter langs heading-vektoren
    import math
    dx = math.cos(math.radians(robot.heading))
    dy = math.sin(math.radians(robot.heading))
    
    fx, fy = field_map.pixel_to_cm(robot.x, robot.y)
    tx, ty = field_map.pixel_to_cm(robot.x + dx * 50, robot.y + dy * 50)
    return math.degrees(math.atan2(ty - fy, tx - fx))
