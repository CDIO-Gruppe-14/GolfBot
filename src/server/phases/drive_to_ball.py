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
from src.planning.command_generator import compute_distance, compute_turn_and_distance, compute_turn_only
from src.planning.pathfinder import find_path_adaptive
from src.server.phases.route_planner import _normalize_obstacles

from src.planning.command_generator import calculate_approach_point
from src.planning.command_generator import calculate_wall_approach_point

from src.server.phases.detection import detect_robot

from config import (MIN_TURN_DEGREES, PRECISION_TURN_SPEED, STOP_DISTANCE_CM,
                    PRECISION_MIN_TURN_DEGREES, ROBOT_FRONT_CM,
                    OBSTACLE_SAFE_RADIUS_CM, WALL_SAFE_RADIUS_CM, ROBOT_RADIUS_CM, TURN_SPEED, MOTOR_SPEED)


def drive_to_ball(ctx, ball, obstacles=None):
    """
    Fase 3: Koer mod bold, koriger undervejs, stop foran med rigtig vinkel.

    Navigerer mod boldens kendte cm-position med loebende
    kamera-feedback for at korrigere retning.

    Args:
        ctx: GameContext med hardware og navigation-state
        ball: (x_cm, y_cm, color) tuple -- maalet
        obstacles: Liste af forhindringer for at udregne approach point

    Returns:
        True hvis bolden er naaet, False ved fejl.
    """
    target_x, target_y = ball.x, ball.y
    approaching = False

    # Normaliser forhindringer til (x, y)-cm-punkter eet sted -- bruges baade til
    # approach-punkt-beregningen og til A*-pathfinding under koerslen.
    obstacle_points = _normalize_obstacles(obstacles)
    field_w, field_h = getattr(ctx.field_map, "field_size_cm", (180, 120))

    if obstacle_points:
        closest_obs = None
        min_dist = float('inf')
        for ox, oy in obstacle_points:
            dist = math.hypot(ball.x - ox, ball.y - oy)
            if dist < min_dist:
                min_dist = dist
                closest_obs = (ox, oy)

        # Hvis bolden er inden for sikkerhedszonen af en forhindring
        if closest_obs and min_dist <= OBSTACLE_SAFE_RADIUS_CM:
            app_x, app_y = calculate_approach_point(ball.x, ball.y, closest_obs[0], closest_obs[1], approach_dist_cm=OBSTACLE_SAFE_RADIUS_CM)
            target_x, target_y = app_x, app_y
            approaching = True
            print(f"\n[KoerTilBold] BOLD TAET PAA FORHINDRING! Koerer til Approach Point ({app_x:.1f}, {app_y:.1f})")

    # Bold taet paa banden? Angrib vinkelret indefra via approach-punkt langs
    # vaegnormalen, saa robotten ikke koerer ind i banden under opsamling (#3).
    # Banderne er kendt fra ArUco-banen (cm-koords 0..field_w / 0..field_h).
    if not approaching:
        wall_app = calculate_wall_approach_point(
            ball.x, ball.y, field_w, field_h,
            wall_safe_dist_cm=WALL_SAFE_RADIUS_CM,
            approach_dist_cm=WALL_SAFE_RADIUS_CM)
        if wall_app is not None:
            target_x, target_y = wall_app
            approaching = True
            print(f"\n[KoerTilBold] BOLD TAET PAA BANDEN! Koerer til Approach Point ({target_x:.1f}, {target_y:.1f})")

    print("\n" + "=" * 60)
    print("[KoerTilBold] Navigation mod {} bold paa ({:.1f}, {:.1f})".format(
        ball.color, target_x, target_y))

    # Committed rute: den praecise A*-sti til maalet planlaegges EN gang og
    # foelges waypoint for waypoint. None = endnu ikke planlagt (eller maal
    # aendret -> planlaeg paa ny). [] = ingen sti fundet -> koer direkte.
    route = None

    while True:
        ctx.iteration += 1
        time.sleep(0.2)

        # --- Find robot position ---
        if not detect_robot(ctx):
            print("[{}] Kan ikke finde robot...".format(ctx.iteration))
            continue

        # --- Beregn drejning og afstand ---
        turn_angle, distance = compute_turn_and_distance(
            ctx.robot.x, ctx.robot.y, ctx.robot.heading, target_x, target_y,
            front_offset_cm=ROBOT_FRONT_CM)

        print("-" * 60)
        print("[{}] Robot: ({:.1f}, {:.1f})  Bold: ({:.1f}, {:.1f})".format(
            ctx.iteration, ctx.robot.x, ctx.robot.y, target_x, target_y))
        print("[{}] Heading: {:.1f}  Turn: {:.1f}  Dist: {:.1f} cm".format(
            ctx.iteration, ctx.robot.heading, turn_angle, distance))

        # --- BOLD NAAET ---
        # Stop kun naar vi baade er taet nok paa og vender direkte mod bolden.
        if distance <= STOP_DISTANCE_CM:
            print(f"[{ctx.iteration}] Robot indenfor stopafstand til approach point.")
            target_x, target_y = ball.x, ball.y
            if approaching:
                print(f"[{ctx.iteration}] Approach point naaet! Skifter maal direkte mod bolden.")
                approaching = False
                route = []  # spring A* over og koer direkte (A* afviser maal i safety-zones)
                
            # Endelig vinkel-verifikation med et FRISK billede (center-baseret)
            # foer vi godkender at vi staar overfor bolden -- TURN er upraecis,
            # saa vi stoler ikke blindt paa at den forrige drejning ramte.
            ok, fresh_turn_angle = _verify_facing_ball(ctx, target_x, target_y)
            if ok:
                print("[{}] >>> BOLD NAAET! (vinkel verificeret) Afstand: {:.1f} cm <<<".format(
                    ctx.iteration, distance))
                return True
            if fresh_turn_angle is None:
                continue  # kamerafejl -- tag nyt billede
            print("[{}] Vinkel ikke bekraeftet ({:.1f} grader) -- korrigerer".format(
                ctx.iteration, fresh_turn_angle))
            if not execute_turn(ctx,PRECISION_TURN_SPEED, fresh_turn_angle):
                return False
            continue

        # # --- PRAECISIONS-TILNAERMELSE (taet paa bold) ---
        # if distance < APPROACH_DISTANCE_CM:
        #     result = _precision_approach(ctx, turn_angle, distance, target_x, target_y)
        #     if result:
        #         return True
        #     continue

        # --- NORMAL NAVIGATION (path-following) ---
        # Vi planlaegger den praecise A*-rute udenom forhindringerne EEN gang og
        # foelger dens waypoints i raekkefoelge. Pathfinderen bestemmer altsaa
        # KOERSELSRETNINGEN; kamera-feedback retter loebende kursen mod hvert
        # waypoint. Ved at committe til eet waypoint ad gangen (i stedet for at
        # genberegne "naeste hop" hver iteration) undgaar vi at robotten
        # oscillerer foran en forhindring.
        if obstacle_points and route is None:
            path, used_safe = find_path_adaptive(
                (ctx.robot.x, ctx.robot.y), (target_x, target_y),
                obstacle_points, field_w, field_h,
                safe_radius=OBSTACLE_SAFE_RADIUS_CM,
                robot_radius=ROBOT_RADIUS_CM)
            if path is None:
                # Bolden er reelt indespaerret af forhindringer. Vi koerer IKKE
                # direkte ind i krydset -- springer bolden over i stedet.
                print("[{}] INGEN sikker sti til bolden -- springer den over"
                      " (undgaar at ramme forhindringen)".format(ctx.iteration))
                return False
            route = list(path)
            extra = "" if used_safe >= OBSTACLE_SAFE_RADIUS_CM else \
                "  [reduceret buffer={:.0f} cm pga. traang bane]".format(used_safe)
            print("[{}] Rute planlagt ({} waypoints){}: {}".format(
                ctx.iteration, len(route), extra,
                " -> ".join("({:.0f},{:.0f})".format(x, y) for x, y in route)))

        # Vaelg naeste delmaal = foerste ikke-naaede waypoint paa ruten.
        # Sidste element er altid selve maalet, saa naar kun det er tilbage
        # overtager stop/precision-logikken oeverst i loopet.
        sub_x, sub_y = target_x, target_y
        if route:
            while len(route) > 1 and math.hypot(
                    ctx.robot.x - route[0][0],
                    ctx.robot.y - route[0][1]) <= 5.0:
                rx, ry = route.pop(0)
                print("[{}] Waypoint ({:.0f},{:.0f}) naaet -- {} tilbage".format(
                    ctx.iteration, rx, ry, len(route)))
            sub_x, sub_y = route[0]

        # Sigt mod delmaalet hvis det ikke er det endelige maal
        # (turn_angle/distance til maalet er allerede beregnet oeverst).
        # VIGTIGT: waypoints er MARKOER-CENTER-positioner (pathfinderen planlaegger
        # centerets sti), saa de navigeres center-baseret (front_offset=0). Hvis vi
        # styrede efter fronten (12 cm foran centret) ville centret aldrig naa
        # waypointet, mens fronten satte sig oven paa det -> vild pejling og
        # robotten roterer i ring. Front-offset bruges KUN til det endelige maal
        # (bolden), saa opsamleren rammer den.
        turn_angle = compute_turn_only(
            ctx.robot.x, ctx.robot.y, ctx.robot.heading, sub_x, sub_y,
            front_offset_cm=0.0)
        print("[{}] Foelger rute -> waypoint ({:.1f}, {:.1f})  Turn: {:.1f}".format(
            ctx.iteration, sub_x, sub_y, turn_angle))

        # Drej hvis vinklen er for stor
        if abs(turn_angle) > MIN_TURN_DEGREES:
            if not execute_turn(ctx,TURN_SPEED ,turn_angle):
                return False
            continue

        distance = compute_distance(ctx.robot.x, ctx.robot.y, sub_x, sub_y)
        if not execute_forward(ctx,MOTOR_SPEED, distance - ROBOT_FRONT_CM):
            return False


def _verify_facing_ball(ctx, target_x, target_y):
    """Tag et FRISK billede og bekraeft at robotten faktisk vender mod bolden.

    Bruges som sidste tjek foer vi godkender at robotten staar overfor bolden,
    saa en upraecis TURN-kommando ikke faar os til at koere fremad i en forkert
    vinkel. Maaler fra robottens front (samme reference som opsamlingen).

    Returnerer (ok, turn_angle, distance). ok=True hvis vinklen er inden for
    PRECISION_MIN_TURN_DEGREES. Ved kamerafejl: (False, None, None).
    """
    if not detect_robot(ctx):
        return False, None
    # VINKEL: center-baseret. Bolden skal ligge paa robottens koerselsakse
    # (linjen gennem center og front langs heading), saa den glider ind i
    # opsamleren naar vi koerer ligeud. Front-baseret vinkel er daarligt
    # konditioneret naar bolden er ~ROBOT_FRONT_OFFSET_CM vaek (front ~oven paa
    # bolden): smaa heading-fejl giver store udsving -> robotten retter for
    # meget og rammer skaevt. (Maalet rammes praecist fordi det tilnaermes paa
    # lang afstand, hvor front-offset er ubetydelig.)
    turn_angle, distance = compute_turn_and_distance(
        ctx.robot.x, ctx.robot.y, ctx.robot.heading, target_x, target_y,
        front_offset_cm=0.0)
        
    return abs(turn_angle) <= PRECISION_MIN_TURN_DEGREES, turn_angle


def _precision_approach(ctx, turn_angle, distance, target_x, target_y):
    """Praecisions-tilnaermelse naar robotten er taet paa bolden.
    Returnerer True hvis bolden er naaet, False for at tage nyt billede."""
    # Fase A: Ret vinkel -- men KUN hvis den er markant forkert.
    # Vinklen beregnes CENTER-baseret (front_offset=0), saa bolden lander paa
    # robottens koerselsakse. Front-baseret finjustering paa kort afstand er
    # daarligt konditioneret og faar robotten til at ramme skaevt (se
    # _verify_facing_ball). Paa kort afstand giver kamera-stoej store
    # vinkelfejl, saa vi bruger en hoejere threshold end normal navigation.
    turn_angle, _ = compute_turn_only(
        ctx.robot.x, ctx.robot.y, ctx.robot.heading, target_x, target_y,
        front_offset_cm=0.0)
    if abs(turn_angle) > PRECISION_MIN_TURN_DEGREES:
        print("[{}] PRECISION TURN {:.1f}".format(ctx.iteration, turn_angle))
        if send_and_verify(ctx.client, "TURN",PRECISION_TURN_SPEED, turn_angle) is None:
            return False
        time.sleep(0.3)
        detect_robot(ctx)
        return False  # Tag nyt billede og tjek vinkel igen

    # Vinklen ser rigtig ud -- men VERIFICER med et frisk billede foer vi
    # committer til fremkoerslen. TURN er upraecis, saa vi stoler ikke blindt
    # paa at den forrige drejning ramte. Er vinklen alligevel forkert, retter
    # vi den og tager et nyt billede i stedet for at koere skaevt mod bolden.
    ok, fresh_turn, fresh_dist = _verify_facing_ball(ctx, target_x, target_y)
    if not ok:
        if fresh_turn is None:
            return False  # kamerafejl -- proev igen
        turn_speed = get_turn_speed(fresh_turn)
        print("[{}] Vinkel ikke bekraeftet ({:.1f} grader) -- korrigerer foer fremkoersel (speed {}%)".format(
            ctx.iteration, fresh_turn, turn_speed))
        if send_and_verify(ctx.client, "TURN", fresh_turn) is None:
            return False
        time.sleep(0.3)
        detect_robot(ctx)
        return False

    # Fase B: Vinkel er bekraeftet -- koer frem til stop-afstanden.
    drive_dist = round(fresh_dist - STOP_DISTANCE_CM, 1)
    if drive_dist <= 0:
        print("[{}] Bolden er allerede inden for stop-afstanden ({:.1f} cm)".format(
            ctx.iteration, STOP_DISTANCE_CM))
        return True

    print("[{}] PRECISION FORWARD {:.1f} cm (dist {:.1f} - stop {:.1f}) [vinkel verificeret]".format(
        ctx.iteration, drive_dist, fresh_dist, STOP_DISTANCE_CM))
    if send_and_verify(ctx.client, "FORWARD", drive_dist) is None:
        return False
    time.sleep(0.5)

    print("[{}] Bold naaet via precision!".format(ctx.iteration))
    return True
