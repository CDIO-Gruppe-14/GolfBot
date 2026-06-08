"""
GolfBot - PC Server / Orchestrator
====================================
Kamera-baseret navigation UDEN gyro.

Approach (v2 — med dobbelt-markør support):
  1. Hvis to markører: heading aflaeses direkte fra kameraet
  2. Hvis én markør: heading kalibreres via initial fremadkoersel
  3. Beregn vinkel til bold, TURN hvis noedvendigt
  4. Efter TURN: verificer heading med kamera (ikke blind matematik)
  5. FORWARD (max step), derefter tag NYT billede og opdater heading
  6. Gentag

Start:
  python src/server/main.py
"""

import sys
import os
import time
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.vision.camera import RobotCamera
from src.vision.color_detector import ColorDetector
from src.vision.robot_tracker import RobotTracker
from src.vision.ball_detector import BallDetector
from src.vision.field_map import FieldMap
from src.communication.connection import PCClient
from src.communication.protocol import encode_command

from src.planning.command_generator import compute_turn_only, compute_forward_step

from config import (ROBOT_IP, MARKER_COLOR, MARKER_COLOR_BACK,
                    MIN_TURN_DEGREES, MIN_DISTANCE_CM, APPROACH_DISTANCE_CM,
                    COLLECTOR_OFFSET_CM, DELIVER_DISTANCE_CM)
import json


# ---------------------------------------------------------------------------
# Hjælpefunktioner
# ---------------------------------------------------------------------------

def get_fresh_frame(camera, flushes=3):
    """Flusher kameraets buffer og returnerer det nyeste frame."""
    for _ in range(flushes):
        camera.get_frame()
    return camera.get_frame()


def _extract_heading(robot, field_map):
    """Beregn heading i cm-koordinater fra dobbelt-markør. Returnerer None hvis kun én markør."""
    if robot.back_x is None:
        return None
    fx, fy = field_map.pixel_to_cm(robot.x, robot.y)
    bx, by = field_map.pixel_to_cm(robot.back_x, robot.back_y)
    return math.degrees(math.atan2(fy - by, fx - bx))

def compute_waypoint(gx, gy, field_width=180.0, field_height=120.0, offset_cm=30.0):
    """Beregner et waypoint X cm foran målet, peget ind mod banens midte."""
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


def find_robot(camera, tracker, field_map):
    """Tag nyt billede og find robot. Returnerer (rx, ry, heading) eller None.
    heading er None hvis kun én markør er fundet."""
    frame = get_fresh_frame(camera)
    if frame is None:
        return None

    robot = tracker.locate(frame)
    if robot is None:
        return None

    rx, ry = field_map.pixel_to_cm(robot.x, robot.y)
    heading = _extract_heading(robot, field_map)
    return (rx, ry, heading)


def find_robot_and_ball(camera, tracker, ball_det, field_map):
    """Tag nyt billede og find robot + bold.
    Returnerer (rx, ry, bx, by, heading) eller None."""
    frame = get_fresh_frame(camera)
    if frame is None:
        return None

    robot = tracker.locate(frame)
    if robot is None:
        return None

    ball = ball_det.find_nearest_ball(frame, robot_pos=(robot.x, robot.y))
    if ball is None:
        return None

    rx, ry = field_map.pixel_to_cm(robot.x, robot.y)
    bx, by = field_map.pixel_to_cm(ball.x, ball.y)
    heading = _extract_heading(robot, field_map)
    return (rx, ry, bx, by, heading)


def send_and_verify(client, cmd, value=None):
    """Send kommando og verificer svar. Returnerer reply eller None ved fejl."""
    client.send_command(encode_command(cmd, value))
    reply = client.wait_for_reply()
    if reply is None or reply.strip() != "DONE":
        print("FEJL: EV3 svarede '{}' paa kommando {} {}".format(reply, cmd, value))
        return None
    return reply

def load_goals():
    """Hent målikoordinater fra fil eller config."""
    from config import GOAL_A_CM, GOAL_B_CM
    goals_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "calibration", "goals.json"
    )
    if os.path.exists(goals_file):
        try:
            with open(goals_file) as f:
                data = json.load(f)
                a = tuple(data["goals_cm"]["A"])
                b = tuple(data["goals_cm"]["B"])
                print("Indlæste mål fra kalibrering: A={:.1f},{:.1f}  B={:.1f},{:.1f}".format(a[0], a[1], b[0], b[1]))
                return a, b
        except Exception as e:
            print("Fejl ved indlæsning af goals.json:", e)
    
    print("Bruger standardmål fra config.py")
    return GOAL_A_CM, GOAL_B_CM

# ---------------------------------------------------------------------------
# Hoved-loop
# ---------------------------------------------------------------------------

def main():
    camera    = RobotCamera()
    detector  = ColorDetector()
    loaded = detector.load_all_profiles()
    print("Indlaedte farveprofiler: {}".format(loaded))

    tracker   = RobotTracker(detector, marker_color=MARKER_COLOR,
                             marker_color_back=MARKER_COLOR_BACK)
    ball_det  = BallDetector(detector)
    field_map = FieldMap()
    client    = PCClient(ROBOT_IP)

    print("Forbinder til EV3...")
    if not client.connect_to_robot():
        print("Kunne ikke forbinde til robotten. Afslutter.")
        return

    print("Forbundet! Starter kamera-navigation.\n")
    print("=" * 60)

    goal_a_cm, goal_b_cm = load_goals()
    
    # Udregn waypoint 35 cm foran målet (for at få en god lige indkørsel)
    goal_a_waypoint = compute_waypoint(goal_a_cm[0], goal_a_cm[1], offset_cm=20.0)

    STATE_SEARCHING = 0
    STATE_DELIVERING_WAYPOINT = 1
    STATE_DELIVERING_GOAL = 2
    STATE_EJECTING = 3
    
    current_state = STATE_SEARCHING
    estimated_heading = None  # Ukendt indtil vi har dobbelt-markør eller bevaeger os
    iteration = 0
    last_known_ball_distance = None
    
    print("Starter opsamlingsmotor (kører konstant)...")
    client.send_command(encode_command("COLLECT_START"))
    time.sleep(0.5)

    try:
        while True:
            iteration += 1
            time.sleep(0.2)

            if current_state == STATE_EJECTING:
                print("[{}] EJECTING BALL!".format(iteration))
                
                # Drej præcist mod målet først for at ramme åbningen
                if estimated_heading is not None:
                    # Vi har allerede regnet vinklen til målet ud før vi stoppede.
                    # Men hvis vi vil være sikre, kan vi tage et billede mere.
                    pass 

                send_and_verify(client, "COLLECT_EJECT")
                print("[{}] Venter 3 sekunder på at bolden triller ud...".format(iteration))
                time.sleep(3.0)
                
                print("[{}] Eject færdig, bakker 10 cm væk...".format(iteration))
                send_and_verify(client, "FORWARD", -10.0)
                time.sleep(1.0)
                
                print("[{}] Genstarter opsamlingsmotor og leder efter ny bold.".format(iteration))
                send_and_verify(client, "COLLECT_START")
                time.sleep(0.5)
                
                current_state = STATE_SEARCHING
                continue

            # --- Find robot og bold/mål ---
            if current_state == STATE_SEARCHING:
                result = find_robot_and_ball(camera, tracker, ball_det, field_map)
                
                # Tjek om vi mistede synet af bolden LIGE FØR vi skulle spise den
                if result is None:
                    if last_known_ball_distance is not None and last_known_ball_distance < 20.0:
                        print("[{}] Bold forsvandt tæt på robotten ({:.1f} cm). Antager den er opsamlet! Skifter til WAYPOINT.".format(iteration, last_known_ball_distance))
                        current_state = STATE_DELIVERING_WAYPOINT
                        last_known_ball_distance = None
                        continue
                    
                    print("[{}] Kan ikke finde robot eller bold...".format(iteration))
                    continue
                    
                rx, ry, bx, by, direct_heading = result
                current_dist = math.hypot(bx - rx, by - ry)
                
                # Tjek om nærmeste bold pludselig "teleporterede" (fordi vi spiste den første og nu ser næste bold)
                if last_known_ball_distance is not None and last_known_ball_distance < 20.0 and current_dist > last_known_ball_distance + 15.0:
                    print("[{}] Nærmeste bold sprang fra {:.1f} cm til {:.1f} cm. Antager vi spiste den første! Skifter til WAYPOINT.".format(iteration, last_known_ball_distance, current_dist))
                    current_state = STATE_DELIVERING_WAYPOINT
                    last_known_ball_distance = None
                    continue
                    
                last_known_ball_distance = current_dist
                
            elif current_state in [STATE_DELIVERING_WAYPOINT, STATE_DELIVERING_GOAL]:
                robot_res = find_robot(camera, tracker, field_map)
                if robot_res is None:
                    print("[{}] Kan ikke finde robot under aflevering...".format(iteration))
                    continue
                rx, ry, direct_heading = robot_res
                
                if current_state == STATE_DELIVERING_WAYPOINT:
                    bx, by = goal_a_waypoint
                else:
                    bx, by = goal_a_cm
            else:
                continue

            # --- Brug direkte heading fra dobbelt-markør hvis tilgaengelig ---
            if direct_heading is not None:
                estimated_heading = direct_heading

            # --- INITIAL KALIBRERING (kun noedvendig med enkelt markør) ---
            if estimated_heading is None:
                print("[{}] Ukendt retning. Koerer fremad 10 cm for at kalibrere...".format(iteration))
                if send_and_verify(client, "FORWARD", 10.0) is None:
                    break
                time.sleep(0.3)

                robot_after = find_robot(camera, tracker, field_map)
                if robot_after is not None:
                    new_rx, new_ry, dh = robot_after
                    if dh is not None:
                        estimated_heading = dh
                        print(" -> Heading fra dobbelt-markør: {:.1f} grader".format(estimated_heading))
                    elif math.hypot(new_rx - rx, new_ry - ry) > 3.0:
                        estimated_heading = math.degrees(math.atan2(new_ry - ry, new_rx - rx))
                        print(" -> Retning kalibreret til: {:.1f} grader".format(estimated_heading))
                    else:
                        print(" -> Bevaegelse for lille til at kalibrere. Proever igen.")
                continue

            # --- NORMAL NAVIGATION ---
            turn_angle, distance = compute_turn_only(rx, ry, estimated_heading, bx, by)

            print("-" * 60)
            state_names = {0: "SEARCHING", 1: "WAYPOINT", 2: "DELIVERING_GOAL"}
            state_name = state_names.get(current_state, "UNKNOWN")
            print("[{}] State: {} | Robot: ({:.1f}, {:.1f})  Target: ({:.1f}, {:.1f})".format(
                iteration, state_name, rx, ry, bx, by))
            print("[{}] Heading: {:.1f}  Turn: {:.1f}  Dist: {:.1f} cm".format(
                iteration, estimated_heading if estimated_heading else 0, turn_angle, distance))

            # --- WAYPOINT LOGIC ---
            if current_state == STATE_DELIVERING_WAYPOINT:
                # Når vi er tæt på waypointet, skift til selve målet
                if distance < 8.0:
                    print("[{}] >>> WAYPOINT NÅET! Retter direkte ind mod målet. <<<".format(iteration))
                    current_state = STATE_DELIVERING_GOAL
                    continue

            # --- DELIVERING GOAL LOGIC ---
            if current_state == STATE_DELIVERING_GOAL:
                if distance < DELIVER_DISTANCE_CM:
                    print("[{}] >>> MÅL NÅET! Skifter til EJECTING. <<<".format(iteration))
                    # Ret vinkel mod mål præcist
                    if abs(turn_angle) > MIN_TURN_DEGREES:
                        send_and_verify(client, "TURN", turn_angle)
                        time.sleep(0.5)
                    current_state = STATE_EJECTING
                    continue

            # --- BOLD NÅET (I SEARCHING) ---
            if current_state == STATE_SEARCHING and distance < MIN_DISTANCE_CM:
                print("[{}] >>> BOLD NÅET! Skifter til WAYPOINT <<<".format(iteration))
                time.sleep(1.0)
                if direct_heading is None:
                    estimated_heading = None
                current_state = STATE_DELIVERING_WAYPOINT
                continue

            # --- PRÆCISIONS-TILNÆRMELSE (tæt på bold under SEARCHING) ---
            if current_state == STATE_SEARCHING and distance < APPROACH_DISTANCE_CM:
                # Fase A: Ret vinkel praecist mod bolden
                if abs(turn_angle) > MIN_TURN_DEGREES:
                    print("[{}] PRECISION TURN {:.1f}".format(iteration, turn_angle))
                    if send_and_verify(client, "TURN", turn_angle) is None:
                        break
                    estimated_heading += turn_angle
                    estimated_heading = (estimated_heading + 180) % 360 - 180
                    time.sleep(0.3)
                    robot_after_turn = find_robot(camera, tracker, field_map)
                    if robot_after_turn is not None:
                        _, _, dh = robot_after_turn
                        if dh is not None:
                            estimated_heading = dh
                    continue  # Tag nyt billede og tjek vinkel igen

                # Fase B: Vinkel er rettet — koer den praecise afstand + offset
                drive_dist = round(distance + COLLECTOR_OFFSET_CM, 1)
                print("[{}] PRECISION FORWARD {:.1f} cm (dist {:.1f} + offset {:.1f})".format(
                    iteration, drive_dist, distance, COLLECTOR_OFFSET_CM))
                if send_and_verify(client, "FORWARD", drive_dist) is None:
                    break
                time.sleep(0.5)
                
                print("[{}] Bold opsamlet via precision! Skifter til WAYPOINT.".format(iteration))
                current_state = STATE_DELIVERING_WAYPOINT
                continue

            # --- FASE 1: DREJ hvis vinklen er for stor ---
            if abs(turn_angle) > MIN_TURN_DEGREES:
                print("[{}] TURN {}".format(iteration, turn_angle))
                if send_and_verify(client, "TURN", turn_angle) is None:
                    break

                # Opdater heading tentativt (fallback)
                estimated_heading += turn_angle
                estimated_heading = (estimated_heading + 180) % 360 - 180

                # FIX #1: Verificer heading med kamera efter drejning
                time.sleep(0.3)
                robot_after_turn = find_robot(camera, tracker, field_map)
                if robot_after_turn is not None:
                    _, _, dh = robot_after_turn
                    if dh is not None:
                        estimated_heading = dh
                        print("[{}] Heading verificeret med kamera: {:.1f} grader".format(
                            iteration, estimated_heading))
                continue

            # --- FASE 2: KOER FREMAD ---
            step = compute_forward_step(distance)
            print("[{}] FORWARD {}".format(iteration, step))

            if send_and_verify(client, "FORWARD", step) is None:
                break
            time.sleep(0.3)

            # FIX #2: Opdater heading med forbedret maaling
            robot_after_fwd = find_robot(camera, tracker, field_map)
            if robot_after_fwd is not None:
                new_rx, new_ry, dh = robot_after_fwd

                # Direkte heading fra dobbelt-markør har altid prioritet
                if dh is not None:
                    estimated_heading = dh
                    print("[{}] Heading fra markør: {:.1f} grader".format(
                        iteration, estimated_heading))
                else:
                    dx = new_rx - rx
                    dy = new_ry - ry
                    move_dist = math.hypot(dx, dy)
                    # Dynamisk threshold: min 30% af step, max 3 cm
                    move_threshold = min(step * 0.3, 3.0)
                    if move_dist > move_threshold:
                        measured = math.degrees(math.atan2(dy, dx))
                        # Staerkere vaegt naar bevaegelsen er stor (mere signal)
                        weight = 0.9 if move_dist > 5.0 else 0.8
                        estimated_heading = weight * measured + (1 - weight) * estimated_heading
                        print("[{}] Heading rettet til: {:.1f} grader (weight={})".format(
                            iteration, estimated_heading, weight))
            else:
                print("[{}] ADVARSEL: Kunne ikke finde robot efter FORWARD!".format(iteration))

    except KeyboardInterrupt:
        print("\nAfbrudt af bruger.")
    finally:
        client.send_command(encode_command("STOP"))
        client.close()
        camera.release()
        print("Server afsluttet.")


if __name__ == "__main__":
    main()
