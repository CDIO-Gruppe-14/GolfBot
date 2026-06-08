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
                    COLLECTOR_OFFSET_CM)


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

    estimated_heading = None  # Ukendt indtil vi har dobbelt-markør eller bevaeger os
    iteration = 0

    try:
        while True:
            iteration += 1
            time.sleep(0.2)

            # --- Find robot og bold ---
            result = find_robot_and_ball(camera, tracker, ball_det, field_map)
            if result is None:
                print("[{}] Kan ikke finde robot eller bold...".format(iteration))
                continue

            rx, ry, bx, by, direct_heading = result

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
            print("[{}] Robot: ({:.1f}, {:.1f})  Bold: ({:.1f}, {:.1f})".format(
                iteration, rx, ry, bx, by))
            print("[{}] Heading: {:.1f}  Turn: {:.1f}  Dist: {:.1f} cm".format(
                iteration, estimated_heading, turn_angle, distance))

            # --- BOLD NAAET ---
            if distance < MIN_DISTANCE_CM:
                print("[{}] >>> BOLD NAAET! <<<".format(iteration))
                if send_and_verify(client, "COLLECT") is None:
                    break
                time.sleep(1.0)
                # Behold heading hvis vi har dobbelt-markør, ellers nulstil
                if direct_heading is None:
                    estimated_heading = None
                continue

            # --- PRAECISIONS-TILNAERMELSE (tæt på bold) ---
            if distance < APPROACH_DISTANCE_CM:
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
