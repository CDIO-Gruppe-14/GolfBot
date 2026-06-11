"""
GolfBot -- Navigation Hjaelpefunktioner
=========================================
Faelles navigation-primitiver brugt af baade
drive_to_ball (Fase 3) og drive_to_goal (Fase 5).

Indeholder: heading-kalibrering, drejning med verifikation,
og fremadkoersel med heading-opdatering.
"""

import math
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.server.helpers.command_utils import send_and_verify
from src.planning.command_generator import compute_forward_step


# calibrate_heading er fjernet - ArUco markør giver altid heading


def execute_turn(ctx, turn_angle):
    """Udforer drejning og verificerer heading med kamera.
    Returnerer True ved succes, False ved fejl."""
    print("[{}] TURN {:.1f}".format(ctx.iteration, turn_angle))
    if send_and_verify(ctx.client, "TURN", turn_angle) is None:
        return False

    # Verificer heading med kamera
    time.sleep(0.3)
    robot_after = find_robot(ctx.camera, ctx.tracker, ctx.field_map)
    if robot_after is not None:
        _, _, dh = robot_after
        ctx.estimated_heading = dh
        print("[{}] Heading verificeret med kamera: {:.1f} grader".format(
            ctx.iteration, ctx.estimated_heading))
    return True


def execute_forward(ctx, distance, rx, ry):
    """Koer fremad og opdater heading fra kamera.
    Returnerer True ved succes, False ved fejl."""
    step = compute_forward_step(distance)
    print("[{}] FORWARD {}".format(ctx.iteration, step))

    if send_and_verify(ctx.client, "FORWARD", step) is None:
        return False
    time.sleep(0.3)

    # Opdater heading med kamera
    robot_after = find_robot(ctx.camera, ctx.tracker, ctx.field_map)
    if robot_after is not None:
        new_rx, new_ry, dh = robot_after
        ctx.estimated_heading = dh
        print("[{}] Heading fra markoer: {:.1f} grader".format(
            ctx.iteration, ctx.estimated_heading))
    else:
        print("[{}] ADVARSEL: Kunne ikke finde robot efter FORWARD!".format(
            ctx.iteration))
    return True
