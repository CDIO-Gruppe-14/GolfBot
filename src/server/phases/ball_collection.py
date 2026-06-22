"""
GolfBot -- Fase 4: Opsamling af Bold
=======================================
Koerer roligt frem over bold og markerer som opsamlet.
Transportbaandet koerer allerede fra opstart (startet i main.py).
"""

import time
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.server.helpers.command_utils import send_and_verify
from src.server.helpers.navigation import execute_turn, execute_forward
from src.server.phases.detection import detect_robot
from src.server.phases.route_planner import _normalize_obstacles
from src.planning.pathfinder import is_position_safe, find_safe_point, find_path_adaptive
from src.planning.command_generator import compute_turn_only, compute_distance
from src.entities.ball import Ball
from config import (COLLECTOR_MOVEMENT_CM, COLLECTOR_SPEED, SPEED_UNDER_COLLECTION,
                    OBSTACLE_SAFE_RADIUS_CM, ROBOT_RADIUS_CM, ROBOT_BACK_CM,
                    WAYPOINT_REACHED_CM, MIN_TURN_DEGREES, TURN_SPEED, MOTOR_SPEED)


from src.communication.protocol import encode_command

def check_stall_over_network(client):
    """Spørger EV3'en via netværket, om motoren i øjeblikket sidder fast."""
    if client.send_command(encode_command("COLLECT_IS_STALLED")):
        reply = client.wait_for_reply()
        if reply:
            return reply.strip() == "TRUE"
    return False

def retreat_to_safe(ctx, obstacles):
    """Sikrer at robotten ender et SIKKERT sted efter opsamling.

    Efter opsamling kan robotten staa med center inde i en forhindrings
    buffer eller for taet paa en vaeg (bolde angribes vinkelret indefra).
    Vi finder det naermeste sikre punkt og koerer dertil via den SAMME
    pathfinder som drive_to_ball, saa drive_to_ball altid kan gaa ud fra
    en sikker startposition.
    """
    if not detect_robot(ctx):
        print("[Retreat] Kan ikke finde robot -- springer retreat over.")
        return

    field_w, field_h = getattr(ctx.field_map, "field_size_cm", (180, 120))
    obstacle_points = _normalize_obstacles(obstacles)

    if is_position_safe((ctx.robot.x, ctx.robot.y),
                        obstacle_points, field_w, field_h, ROBOT_RADIUS_CM):
        print("[Retreat] Robotten staar allerede sikkert.")
        return

    safe = find_safe_point((ctx.robot.x, ctx.robot.y),
                           obstacle_points, field_w, field_h, ROBOT_RADIUS_CM)
    if safe is None:
        print("[Retreat] ADVARSEL: Intet sikkert punkt fundet -- bakker {:.0f} cm.".format(
            ROBOT_BACK_CM))
        execute_forward(ctx, MOTOR_SPEED, -ROBOT_BACK_CM)
        return

    path, _ = find_path_adaptive(
        (ctx.robot.x, ctx.robot.y), safe,
        obstacle_points, field_w, field_h,
        safe_radius=OBSTACLE_SAFE_RADIUS_CM, robot_radius=ROBOT_RADIUS_CM)
    if path is None:
        print("[Retreat] ADVARSEL: Ingen sti til sikkert punkt -- bakker {:.0f} cm.".format(
            ROBOT_BACK_CM))
        execute_forward(ctx, MOTOR_SPEED, -ROBOT_BACK_CM)
        return

    print("[Retreat] Koerer til sikkert punkt ({:.1f}, {:.1f}) via {} waypoints.".format(
        safe[0], safe[1], len(path)))

    # Egen lille koere-loop: foelg waypoints center-baseret (front_offset=0),
    # ligesom drive_to_ball's waypoint-navigation.
    route = list(path)
    max_iterations = 30
    for _ in range(max_iterations):
        if not detect_robot(ctx):
            continue

        # Pop naaede waypoints (sidste = selve det sikre punkt).
        while len(route) > 1 and math.hypot(
                ctx.robot.x - route[0][0],
                ctx.robot.y - route[0][1]) <= WAYPOINT_REACHED_CM:
            route.pop(0)

        sub_x, sub_y = route[0]
        if math.hypot(ctx.robot.x - sub_x, ctx.robot.y - sub_y) <= WAYPOINT_REACHED_CM:
            print("[Retreat] Sikkert punkt naaet.")
            return

        # Vi BAKKER mod det sikre punkt, saa robottens BAGENDE skal pege mod
        # maalet -- altsaa heading + 180. Drejevinklen beregnes derfor mod den
        # omvendte heading, og selve koerslen er negativ (baglaens).
        front_turn = compute_turn_only(
            ctx.robot.x, ctx.robot.y, ctx.robot.heading, sub_x, sub_y)
        back_turn = front_turn + 180 if front_turn < 0 else front_turn - 180
        if abs(back_turn) > MIN_TURN_DEGREES:
            if not execute_turn(ctx, TURN_SPEED, back_turn):
                return
            continue

        distance = compute_distance(
            ctx.robot.x, ctx.robot.y, sub_x, sub_y, ctx.robot.heading,
            front_offset_cm=0)
        if not execute_forward(ctx, MOTOR_SPEED, -distance):
            return

    print("[Retreat] ADVARSEL: Naaede ikke sikkert punkt inden for max iterationer.")


def collect_ball(ctx, ball, obstacles=None):
    """
    Fase 4: Opsam bolden.

    Transportbaandet koerer allerede (startet i main.py ved opstart).
    1. Koer roligt frem over bolden
    2. Marker som opsamlet i prioritetskoeen
    3. Traek robotten tilbage til en sikker position (retreat_to_safe)

    Args:
        ctx: GameContext
        ball: Ball-objekt fra køen
        obstacles: Liste af forhindringer -- bruges til at finde sikker slutposition
    """
    ctx.iteration += 1
    print(f"\n [Opsamling] Opsamler bold paa ({ball.x}, {ball.y})")

    
    print("[{}] [Opsamling] Starter motor".format(ctx.iteration))
    
    send_and_verify(ctx.client, "COLLECT_START", COLLECTOR_SPEED)

    print("[{}] [Opsamling] Koerer roligt frem over bolden...".format(ctx.iteration))
    send_and_verify(ctx.client, "FORWARD", SPEED_UNDER_COLLECTION, COLLECTOR_MOVEMENT_CM)
    
    # I stedet for bare at vente 3 sekunder, poller vi for stall.
    print("[{}] [Opsamling] Venter og tjekker om motoren staller...".format(ctx.iteration))
    timeout_time = time.time() + 3.0
    stall_start_time = None
    
    while time.time() < timeout_time:
        is_stalled = check_stall_over_network(ctx.client)
        if is_stalled:
            if stall_start_time is None:
                stall_start_time = time.time()
                print("[{}] [Opsamling] EV3 melder 'stalled'! Starter timer...".format(ctx.iteration))
            elif time.time() - stall_start_time >= 0.5: # Hvis stalled i 0.5 sekunder
                print("[{}] [Opsamling] Bolden sidder fast! Kører yderligere 5 cm fremad...".format(ctx.iteration))
                send_and_verify(ctx.client, "FORWARD", 15, 2.5)
                # Vent lidt ekstra efter vi er kørt frem, og stop så
                time.sleep(.5)
                send_and_verify(ctx.client, "FORWARD", 15, -2.5)
                break
        else:
            stall_start_time = None
        time.sleep(0.1)

    send_and_verify(ctx.client, "COLLECT_STOP")

    print("[{}] [Opsamling] Bold opsamlet. Kører imod safe zone".format(ctx.iteration))

    # Sikr en sikker slutposition, saa naeste drive_to_ball starter sikkert.
    retreat_to_safe(ctx, obstacles)
    
    print("[{}] [Opsamling] Bold opsamling afsluttet!".format(ctx.iteration))

