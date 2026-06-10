"""
GolfBot -- Maal-hjaelpefunktioner
====================================
Indlaes maalkoordinater og beregn waypoints.
Flyttet fra server/main.py for bedre separation.
"""

import os
import json
import math


def compute_waypoint(gx, gy, field_width=180.0, field_height=120.0, offset_cm=30.0):
    """Beregner et waypoint X cm foran maalet, peget ind mod banens midte."""
    cx = field_width / 2.0
    cy = field_height / 2.0

    dx = cx - gx
    dy = cy - gy
    length = math.hypot(dx, dy)
    if length == 0:
        return gx, gy

    nx = (dx / length) * offset_cm
    ny = (dy / length) * offset_cm
    return gx + nx, gy + ny


def load_goals():
    """Hent maalkoordinater fra fil eller config (bruges som fallback hvis ArUco fejler)."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))))
    from config import GOAL_A_CM, GOAL_B_CM

    # CDIO/ er 4 niveauer op fra src/server/helpers/
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))))
    goals_file = os.path.join(project_root, "calibration", "goals.json")

    if os.path.exists(goals_file):
        try:
            with open(goals_file) as f:
                data = json.load(f)
                a = tuple(data["goals_cm"]["A"])
                b = tuple(data["goals_cm"]["B"])
                print("Indlaedte maal fra kalibrering: A={:.1f},{:.1f}  B={:.1f},{:.1f}".format(
                    a[0], a[1], b[0], b[1]))
                return a, b
        except Exception as e:
            print("Fejl ved indlaesning af goals.json: {}".format(e))

    print("Bruger standardmaal fra config.py")
    return GOAL_A_CM, GOAL_B_CM
