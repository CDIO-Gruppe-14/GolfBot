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
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.server.helpers.navigation import (
    execute_turn, execute_forward
)
from src.server.phases.detection import detect_robot
from src.planning.command_generator import compute_distance, compute_turn_only
from src.planning.pathfinder import find_path_adaptive
from src.server.phases.route_planner import _normalize_obstacles
from config import (MIN_TURN_DEGREES, DELIVER_DISTANCE_CM, PRECISION_TURN_SPEED, ROBOT_FRONT_CM,
                    WAYPOINT_REACHED_CM, OBSTACLE_SAFE_RADIUS_CM, ROBOT_RADIUS_CM, TURN_SPEED, PRECISION_TURN_SPEED, MOTOR_SPEED)


def drive_to_goal(ctx, obstacles=None):
    """
    Fase 5: Koer mod maal med waypoint-approach.

    1. Koer til waypoint (punkt foran maalet for lige indkoersel) -- UDENOM
       forhindringer via A*-waypoints.
    2. Naar waypoint er naaet, koer direkte mod maalet
    3. Stop naar robotten er inden for DELIVER_DISTANCE_CM

    Args:
        ctx: GameContext med maalkoordinater og navigation-state
        obstacles: Liste af forhindringer (cm) til at laegge ruten udenom.
    """
    print("\n" + "=" * 60)
    print("[KoerTilMaal] Starter navigation mod maal")

    obstacle_points = _normalize_obstacles(obstacles)
    field_w, field_h = getattr(ctx.field_map, "field_size_cm", (180, 120))

    # Trin 1: Koer til waypoint -- med forhindrings-undvigelse. Waypointet ligger
    # sikkert inde paa banen, saa pathfinding kan bruges her.
    print("[KoerTilMaal] Trin 1: Waypoint ({:.1f}, {:.1f})".format(
        ctx.goal_a_waypoint[0], ctx.goal_a_waypoint[1]))
    _navigate_to_point(ctx, ctx.goal_a_waypoint[0], ctx.goal_a_waypoint[1],
                       stop_distance=WAYPOINT_REACHED_CM, label="WAYPOINT",
                       obstacle_points=obstacle_points,
                       field_w=field_w, field_h=field_h)

    # Trin 2: Koer direkte mod maalet. INGEN pathfinding her -- maalet ligger paa/
    # uden for banden, og waypointet har allerede rettet os ind for en lige
    # indkoersel. De sidste cm skal vaere en ren ligeud-koersel ind i maalet.
    print("[KoerTilMaal] Trin 2: Maal ({:.1f}, {:.1f})".format(
        ctx.goal_a_cm[0], ctx.goal_a_cm[1]))
    _navigate_to_point(ctx, ctx.goal_a_cm[0], ctx.goal_a_cm[1],
                       stop_distance=DELIVER_DISTANCE_CM, label="MAAL", turn_speed=PRECISION_TURN_SPEED, obstacle_points=None)

    print("[KoerTilMaal] Maal naaet!")


def _navigate_to_point(ctx, target_x, target_y, stop_distance, label, turn_speed=TURN_SPEED,    
                       obstacle_points=None, field_w=180, field_h=120):
    """Intern navigation-loop mod et punkt. Stopper ved stop_distance.

    Hvis obstacle_points er angivet, laegges ruten UDENOM forhindringerne via
    A*-waypoints (samme committed path-following som drive_to_ball): stien
    planlaegges een gang og foelges waypoint for waypoint. Waypoints navigeres
    center-baseret (de er markoer-center-positioner)."""
    route = None  # None = ikke planlagt; [] = ingen sti -> koer direkte
    while True:
        ctx.iteration += 1
        time.sleep(0.2)

        if not detect_robot(ctx):
            print("[{}] Kan ikke finde robot under {} ...".format(
                ctx.iteration, label))
            continue

        turn_angle = compute_turn_only(
            ctx.robot.x, ctx.robot.y, ctx.robot.heading, target_x, target_y)
        distance = compute_distance(
            ctx.robot.x, ctx.robot.y, target_x, target_y, ctx.robot.heading,
            front_offset_cm=ROBOT_FRONT_CM)

        print("[{}] {} | Pos: ({:.1f},{:.1f}) -> ({:.1f},{:.1f}) "
              "Dist: {:.1f} Turn: {:.1f}".format(
                  ctx.iteration, label, ctx.robot.x, ctx.robot.y, target_x, target_y,
                  distance, turn_angle))

        # Maal naaet? Stop uden at dreje -- robotten er allerede rettet
        # ind korrekt fra waypoint-approachen. Vinkelberegning er upaalidelig
        # paa saa kort afstand (kamera-stoej dominerer).
        if distance < stop_distance:
            print("[{}] >>> {} NAAET! <<<".format(ctx.iteration, label))
            return

        # --- Forhindrings-undvigelse (committed path-following) ---
        if obstacle_points and route is None:
            path, used_safe = find_path_adaptive(
                (ctx.robot.x, ctx.robot.y), (target_x, target_y),
                obstacle_points, field_w, field_h,
                safe_radius=OBSTACLE_SAFE_RADIUS_CM, robot_radius=ROBOT_RADIUS_CM)
            if path is None:
                print("[{}] {} | INGEN fri sti -- koerer direkte".format(
                    ctx.iteration, label))
                route = []
            else:
                route = list(path)
                extra = "" if used_safe >= OBSTACLE_SAFE_RADIUS_CM else \
                    "  [reduceret buffer={:.0f} cm]".format(used_safe)
                print("[{}] {} | Rute planlagt ({} waypoints){}: {}".format(
                    ctx.iteration, label, len(route), extra,
                    " -> ".join("({:.0f},{:.0f})".format(x, y) for x, y in route)))

        # Vaelg naeste delmaal = foerste ikke-naaede waypoint paa ruten.
        sub_x, sub_y = target_x, target_y
        if route:
            while len(route) > 1 and math.hypot(
                    ctx.robot.x - route[0][0],
                    ctx.robot.y - route[0][1]) <= WAYPOINT_REACHED_CM:
                rx, ry = route.pop(0)
                print("[{}] {} | Waypoint ({:.0f},{:.0f}) naaet -- {} tilbage".format(
                    ctx.iteration, label, rx, ry, len(route)))
            sub_x, sub_y = route[0]

        # Waypoints navigeres center-baseret (front_offset=0); det endelige maal
        # beholder front-offset (afstanden er allerede beregnet oeverst).
        if (sub_x, sub_y) != (target_x, target_y):
            turn_angle = compute_turn_only(
                ctx.robot.x, ctx.robot.y, ctx.robot.heading, sub_x, sub_y)
            distance = compute_distance(
                ctx.robot.x, ctx.robot.y, sub_x, sub_y,ctx.robot.heading,
                front_offset_cm=ROBOT_FRONT_CM)
            print("[{}] {} | Foelger rute -> waypoint ({:.1f}, {:.1f})  "
                  "Turn: {:.1f}  Dist: {:.1f}".format(
                      ctx.iteration, label, sub_x, sub_y, turn_angle, distance))

        # Drej hvis vinklen er for stor
        if abs(turn_angle) > MIN_TURN_DEGREES:
            if not execute_turn(ctx,TURN_SPEED ,turn_angle):
                return False
            continue
        
        print("[{}] Afstand til waypoint: {:.1f} cm".format(ctx.iteration, distance))
        if not execute_forward(ctx, MOTOR_SPEED, distance):
            return False
