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
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.server.helpers.command_utils import send_and_verify
from src.server.helpers.navigation import (
    execute_turn, execute_forward
)
from src.planning.command_generator import compute_turn_only

from src.server.phases.detection import detect_robot

from config import MIN_TURN_DEGREES, APPROACH_DISTANCE_CM, STOP_DISTANCE_CM, PRECISION_MIN_TURN_DEGREES, ROBOT_FRONT_OFFSET_CM, OBSTACLE_SAFE_RADIUS_CM


def drive_to_ball(ctx, ball, obstacles=None):
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
        obstacles: Liste af forhindringer for at udregne approach point

    Returns:
        True hvis bolden er naaet, False ved fejl.
    """
    target_x, target_y = ball.x, ball.y
    approaching = False

    if obstacles:
        closest_obs = None
        min_dist = float('inf')
        for obs in obstacles:
            ox = getattr(obs, "x", obs[0]) if not isinstance(obs, tuple) else obs[0]
            oy = getattr(obs, "y", obs[1]) if not isinstance(obs, tuple) else obs[1]
            dist = math.hypot(ball.x - ox, ball.y - oy)
            if dist < min_dist:
                min_dist = dist
                closest_obs = (ox, oy)
                
        # Hvis bolden er inden for sikkerhedszonen af en forhindring
        if closest_obs and min_dist <= OBSTACLE_SAFE_RADIUS_CM:
            from src.planning.command_generator import calculate_approach_point
            app_x, app_y = calculate_approach_point(ball.x, ball.y, closest_obs[0], closest_obs[1], approach_dist_cm=OBSTACLE_SAFE_RADIUS_CM)
            target_x, target_y = app_x, app_y
            approaching = True
            print(f"\n[KoerTilBold] BOLD TAET PAA FORHINDRING! Koerer til Approach Point ({app_x:.1f}, {app_y:.1f})")

    print("\n" + "=" * 60)
    print("[KoerTilBold] Navigation mod {} bold paa ({:.1f}, {:.1f})".format(
        ball.color, target_x, target_y))

    while True:
        ctx.iteration += 1
        time.sleep(0.2)

        # --- Find robot position ---
        detect_robot(ctx)
        if ctx.robot is None:
            print("[{}] Kan ikke finde robot...".format(ctx.iteration))
            continue

        # --- Beregn drejning og afstand ---
        turn_angle, distance = compute_turn_only(
            ctx.robot.x, ctx.robot.y, ctx.robot.heading, target_x, target_y,
            front_offset_cm=ROBOT_FRONT_OFFSET_CM)

        print("-" * 60)
        print("[{}] Robot: ({:.1f}, {:.1f})  Bold: ({:.1f}, {:.1f})".format(
            ctx.iteration, ctx.robot.x, ctx.robot.y, target_x, target_y))
        print("[{}] Heading: {:.1f}  Turn: {:.1f}  Dist: {:.1f} cm".format(
            ctx.iteration, ctx.robot.heading, turn_angle, distance))

        # --- BOLD NAAET ---
        # Stop kun naar vi baade er taet nok paa og vender direkte mod bolden.
        if distance <= STOP_DISTANCE_CM:
            if approaching:
                print(f"[{ctx.iteration}] Approach point naaet! Skifter maal direkte mod bolden.")
                approaching = False
                target_x, target_y = ball.x, ball.y
                continue
                
            if abs(turn_angle) <= PRECISION_MIN_TURN_DEGREES:
                print("[{}] >>> BOLD NAAET! Afstand: {:.1f} cm <<<".format(
                    ctx.iteration, distance))
                return True

            if not execute_turn(ctx, turn_angle):
                return False
            continue

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
        if not execute_forward(ctx, distance, ctx.robot.x, ctx.robot.y):
            return False


def _precision_approach(ctx, turn_angle, distance):
    """Praecisions-tilnaermelse naar robotten er taet paa bolden.
    Returnerer True hvis bolden er naaet, False for at tage nyt billede."""
    # Fase A: Ret vinkel -- men KUN hvis den er markant forkert.
    # Paa kort afstand giver kamera-stoej store vinkelfejl,
    # saa vi bruger en hoejere threshold end normal navigation.
    if abs(turn_angle) > PRECISION_MIN_TURN_DEGREES:
        print("[{}] PRECISION TURN {:.1f}".format(ctx.iteration, turn_angle))
        if send_and_verify(ctx.client, "TURN", turn_angle) is None:
            return False
        time.sleep(0.3)
        detect_robot(ctx)
        return False  # Tag nyt billede og tjek vinkel igen

    # Fase B: Vinkel er rettet -- koer frem til stop-afstanden.
    drive_dist = round(distance - STOP_DISTANCE_CM, 1)
    if drive_dist <= 0:
        print("[{}] Bolden er allerede inden for stop-afstanden ({:.1f} cm)".format(
            ctx.iteration, STOP_DISTANCE_CM))
        return True

    print("[{}] PRECISION FORWARD {:.1f} cm (dist {:.1f} - stop {:.1f})".format(
        ctx.iteration, drive_dist, distance, STOP_DISTANCE_CM))
    if send_and_verify(ctx.client, "FORWARD", drive_dist) is None:
        return False
    time.sleep(0.5)

    print("[{}] Bold naaet via precision!".format(ctx.iteration))
    return True
