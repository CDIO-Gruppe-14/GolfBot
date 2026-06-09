"""
GolfBot -- Fase 5: Koer til Maal
==================================
Navigerer robotten mod maalet via et waypoint
for at sikre en lige indkoersel.

Trin:
  1. Koer til waypoint (punkt foran maalet)
  2. Koer direkte mod maalet
  3. Stop naar robotten er inden for DELIVER_DISTANCE_CM
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.server.helpers.camera_utils import find_robot
from src.server.helpers.navigation import (
    calibrate_heading, execute_turn, execute_forward
)
from src.planning.command_generator import compute_turn_only

from config import MIN_TURN_DEGREES, DELIVER_DISTANCE_CM

# Afstand til waypoint hvor vi skifter til direkte maal-koersel (cm)
WAYPOINT_REACHED_CM = 8.0


def drive_to_goal(ctx):
    """
    Fase 5: Koer mod maal med waypoint-approach.

    1. Koer til waypoint (punkt foran maalet for lige indkoersel)
    2. Naar waypoint er naaet, koer direkte mod maalet
    3. Stop naar robotten er inden for DELIVER_DISTANCE_CM

    Args:
        ctx: GameContext med maalkoordinater og navigation-state
    """
    print("\n" + "=" * 60)
    print("[KoerTilMaal] Starter navigation mod maal")

    # Trin 1: Koer til waypoint
    print("[KoerTilMaal] Trin 1: Waypoint ({:.1f}, {:.1f})".format(
        ctx.goal_a_waypoint[0], ctx.goal_a_waypoint[1]))
    _navigate_to_point(ctx, ctx.goal_a_waypoint[0], ctx.goal_a_waypoint[1],
                       stop_distance=WAYPOINT_REACHED_CM, label="WAYPOINT")

    # Trin 2: Koer direkte mod maalet
    print("[KoerTilMaal] Trin 2: Maal ({:.1f}, {:.1f})".format(
        ctx.goal_a_cm[0], ctx.goal_a_cm[1]))
    _navigate_to_point(ctx, ctx.goal_a_cm[0], ctx.goal_a_cm[1],
                       stop_distance=DELIVER_DISTANCE_CM, label="MAAL")

    print("[KoerTilMaal] Maal naaet!")


def _navigate_to_point(ctx, target_x, target_y, stop_distance, label):
    """Intern navigation-loop mod et punkt. Stopper ved stop_distance."""
    while True:
        ctx.iteration += 1
        time.sleep(0.2)

        robot_result = find_robot(ctx.camera, ctx.tracker, ctx.field_map)
        if robot_result is None:
            print("[{}] Kan ikke finde robot under {} ...".format(
                ctx.iteration, label))
            continue

        rx, ry, direct_heading = robot_result
        if direct_heading is not None:
            ctx.estimated_heading = direct_heading

        if ctx.estimated_heading is None:
            calibrate_heading(ctx, rx, ry)
            continue

        turn_angle, distance = compute_turn_only(
            rx, ry, ctx.estimated_heading, target_x, target_y)

        print("[{}] {} | Pos: ({:.1f},{:.1f}) -> ({:.1f},{:.1f}) "
              "Dist: {:.1f} Turn: {:.1f}".format(
                  ctx.iteration, label, rx, ry, target_x, target_y,
                  distance, turn_angle))

        # Maal naaet?
        if distance < stop_distance:
            if abs(turn_angle) > MIN_TURN_DEGREES:
                execute_turn(ctx, turn_angle)
            print("[{}] >>> {} NAAET! <<<".format(ctx.iteration, label))
            return

        # Drej
        if abs(turn_angle) > MIN_TURN_DEGREES:
            execute_turn(ctx, turn_angle)
            continue

        # Fremad
        execute_forward(ctx, distance, rx, ry)
