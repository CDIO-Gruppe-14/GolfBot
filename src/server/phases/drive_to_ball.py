"""
GolfBot -- Fase 3: Koer til Bold
==================================
Navigerer robotten mod en specifik bold med loebende korrektion.

Funktionalitet:
  - Koer mod bold med kamera-feedback
  - Korrigerer retning undervejs
  - Stop foran bold med rigtig vinkel
  - Variabel til at styre afstand til bold (STOP_DISTANCE_CM)
  - Forberedt til forhindringskorrektion (A*-integration)
"""

import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.server.helpers.camera_utils import find_robot
from src.server.helpers.command_utils import send_and_verify
from src.server.helpers.navigation import (
    calibrate_heading, execute_turn, execute_forward
)
from src.planning.command_generator import compute_turn_only

from config import (MIN_TURN_DEGREES, MIN_DISTANCE_CM,
                    APPROACH_DISTANCE_CM, COLLECTOR_OFFSET_CM)

# Afstand (cm) hvor robotten stopper foran bolden.
# Variabel til at styre praecis afstand (naevnt paa whiteboard).
STOP_DISTANCE_CM = MIN_DISTANCE_CM


def drive_to_ball(ctx, ball):
    """
    Fase 3: Koer mod bold, koriger undervejs, stop foran med rigtig vinkel.

    Navigerer mod boldens kendte cm-position med loebende
    kamera-feedback for at korrigere retning.

    Forberedt til forhindringskorrektion:
      Naar A* er implementeret kan ruten laegges uden om forhindringer.
      Se TODO-kommentar i navigation-loopet.

    Args:
        ctx: GameContext med hardware og navigation-state
        ball: (x_cm, y_cm, color) tuple -- maalet

    Returns:
        True hvis bolden er naaet, False ved fejl.
    """
    target_x, target_y = ball[0], ball[1]
    print("\n" + "=" * 60)
    print("[KoerTilBold] Navigation mod {} bold paa ({:.1f}, {:.1f})".format(
        ball[2], target_x, target_y))

    while True:
        ctx.iteration += 1
        time.sleep(0.2)

        # --- Find robot position ---
        robot_result = find_robot(ctx.camera, ctx.tracker, ctx.field_map)
        if robot_result is None:
            print("[{}] Kan ikke finde robot...".format(ctx.iteration))
            continue

        rx, ry, direct_heading = robot_result

        # Brug direkte heading fra dobbelt-markoer hvis tilgaengelig
        if direct_heading is not None:
            ctx.estimated_heading = direct_heading

        # --- Heading kalibrering (hvis ukendt) ---
        if ctx.estimated_heading is None:
            calibrate_heading(ctx, rx, ry)
            continue

        # --- Beregn drejning og afstand ---
        turn_angle, distance = compute_turn_only(
            rx, ry, ctx.estimated_heading, target_x, target_y)

        print("-" * 60)
        print("[{}] Robot: ({:.1f}, {:.1f})  Bold: ({:.1f}, {:.1f})".format(
            ctx.iteration, rx, ry, target_x, target_y))
        print("[{}] Heading: {:.1f}  Turn: {:.1f}  Dist: {:.1f} cm".format(
            ctx.iteration, ctx.estimated_heading, turn_angle, distance))

        # --- BOLD NAAET ---
        if distance < STOP_DISTANCE_CM:
            print("[{}] >>> BOLD NAAET! Afstand: {:.1f} cm <<<".format(
                ctx.iteration, distance))
            return True

        # --- PRAECISIONS-TILNAERMELSE (taet paa bold) ---
        if distance < APPROACH_DISTANCE_CM:
            result = _precision_approach(ctx, turn_angle, distance)
            if result:
                return True
            continue

        # --- NORMAL NAVIGATION ---

        # TODO: Forhindringskorrektion kan tilfojes her:
        #   from src.planning.pathfinder import AStarPathfinder
        #   pathfinder = AStarPathfinder()
        #   waypoints = pathfinder.find_path(
        #       (rx, ry), (target_x, target_y), ctx_obstacles)
        #   Brug foerste waypoint som midlertidigt maal

        # Drej hvis vinklen er for stor
        if abs(turn_angle) > MIN_TURN_DEGREES:
            if not execute_turn(ctx, turn_angle):
                return False
            continue

        # Koer fremad
        if not execute_forward(ctx, distance, rx, ry):
            return False


def _precision_approach(ctx, turn_angle, distance):
    """Praecisions-tilnaermelse naar robotten er taet paa bolden.
    Returnerer True hvis bolden er naaet, False for at tage nyt billede."""
    # Fase A: Ret vinkel praecist mod bolden
    if abs(turn_angle) > MIN_TURN_DEGREES:
        print("[{}] PRECISION TURN {:.1f}".format(ctx.iteration, turn_angle))
        if send_and_verify(ctx.client, "TURN", turn_angle) is None:
            return False
        ctx.estimated_heading += turn_angle
        ctx.estimated_heading = (ctx.estimated_heading + 180) % 360 - 180
        time.sleep(0.3)
        robot_after = find_robot(ctx.camera, ctx.tracker, ctx.field_map)
        if robot_after is not None:
            _, _, dh = robot_after
            if dh is not None:
                ctx.estimated_heading = dh
        return False  # Tag nyt billede og tjek vinkel igen

    # Fase B: Vinkel er rettet -- koer den praecise afstand
    drive_dist = round(distance + COLLECTOR_OFFSET_CM, 1)
    print("[{}] PRECISION FORWARD {:.1f} cm (dist {:.1f} + offset {:.1f})".format(
        ctx.iteration, drive_dist, distance, COLLECTOR_OFFSET_CM))
    if send_and_verify(ctx.client, "FORWARD", drive_dist) is None:
        return False
    time.sleep(0.5)

    print("[{}] Bold naaet via precision!".format(ctx.iteration))
    return True
