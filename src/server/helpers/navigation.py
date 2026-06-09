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

from src.server.helpers.camera_utils import find_robot
from src.server.helpers.command_utils import send_and_verify
from src.planning.command_generator import compute_forward_step


def calibrate_heading(ctx, rx, ry):
    """Koer fremad 10 cm for at kalibrere heading fra kamera.
    Returnerer True hvis kalibrering lykkedes."""
    print("[{}] Ukendt retning. Koerer fremad 10 cm for at kalibrere...".format(
        ctx.iteration))
    if send_and_verify(ctx.client, "FORWARD", 10.0) is None:
        return False
    time.sleep(0.3)

    robot_after = find_robot(ctx.camera, ctx.tracker, ctx.field_map)
    if robot_after is not None:
        new_rx, new_ry, dh = robot_after
        if dh is not None:
            ctx.estimated_heading = dh
            print(" -> Heading fra dobbelt-markoer: {:.1f} grader".format(
                ctx.estimated_heading))
            return True
        elif math.hypot(new_rx - rx, new_ry - ry) > 3.0:
            ctx.estimated_heading = math.degrees(
                math.atan2(new_ry - ry, new_rx - rx))
            print(" -> Retning kalibreret til: {:.1f} grader".format(
                ctx.estimated_heading))
            return True
        else:
            print(" -> Bevaegelse for lille til at kalibrere. Proever igen.")
    return False


def execute_turn(ctx, turn_angle):
    """Udforer drejning og verificerer heading med kamera.
    Returnerer True ved succes, False ved fejl."""
    print("[{}] TURN {:.1f}".format(ctx.iteration, turn_angle))
    if send_and_verify(ctx.client, "TURN", turn_angle) is None:
        return False

    # Opdater heading tentativt
    ctx.estimated_heading += turn_angle
    ctx.estimated_heading = (ctx.estimated_heading + 180) % 360 - 180

    # Verificer heading med kamera
    time.sleep(0.3)
    robot_after = find_robot(ctx.camera, ctx.tracker, ctx.field_map)
    if robot_after is not None:
        _, _, dh = robot_after
        if dh is not None:
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

        if dh is not None:
            ctx.estimated_heading = dh
            print("[{}] Heading fra markoer: {:.1f} grader".format(
                ctx.iteration, ctx.estimated_heading))
        else:
            dx = new_rx - rx
            dy = new_ry - ry
            move_dist = math.hypot(dx, dy)
            move_threshold = min(step * 0.3, 3.0)
            if move_dist > move_threshold:
                measured = math.degrees(math.atan2(dy, dx))
                weight = 0.9 if move_dist > 5.0 else 0.8
                ctx.estimated_heading = (
                    weight * measured + (1 - weight) * ctx.estimated_heading)
                print("[{}] Heading rettet til: {:.1f} grader (weight={})".format(
                    ctx.iteration, ctx.estimated_heading, weight))
    else:
        print("[{}] ADVARSEL: Kunne ikke finde robot efter FORWARD!".format(
            ctx.iteration))
    return True
