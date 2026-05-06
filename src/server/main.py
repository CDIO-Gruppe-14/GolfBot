"""
GolfBot - PC Server / Orchestrator
====================================
Kamera-baseret navigation UDEN gyro.

Approach:
  1. Start med heading=0
  2. Beregn vinkel til bold, TURN hvis noedvendigt
  3. Efter TURN: heading opdateres med turn-vaerdien (ren matematik)
  4. Naar vinkel er lille: FORWARD (max 20cm), derefter tag NYT billede
     og beregn faktisk heading fra bevaegelsen
  5. Gentag

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
from src.planning.strategy import PickupPlanner

from config import ROBOT_IP, MARKER_COLOR, MIN_TURN_DEGREES, MIN_DISTANCE_CM


def get_fresh_frame(camera, flushes=5):
    """Flusher kameraets buffer ved at tage X billeder og kassere dem. Returnerer det nyeste."""
    for _ in range(flushes):
        camera.get_frame()
    return camera.get_frame()


def capture_scene(camera, tracker, ball_det):
    """Tag et friskt billede og find robot + alle bolde."""

    frame = get_fresh_frame(camera)
    if frame is None:
        return None

    robot = tracker.locate(frame)
    if robot is None:
        return None

    balls = ball_det.find_all_balls(frame)
    return frame, robot, balls


def confirm_pickup(camera, tracker, ball_det, planner, checks=2):
    """Bekræft at den aktive bold er væk i et par friske frames."""

    for _ in range(checks):
        scene = capture_scene(camera, tracker, ball_det)
        if scene is None:
            continue
        _frame, _robot, balls = scene
        if planner.target_is_visible(balls):
            return False
    return True


def main():
    camera    = RobotCamera()
    detector  = ColorDetector()
    loaded = detector.load_all_profiles()
    print("Indlaedte farveprofiler: {}".format(loaded))

    tracker   = RobotTracker(detector, marker_color=MARKER_COLOR)
    ball_det  = BallDetector(detector)
    field_map = FieldMap()
    planner   = PickupPlanner(field_map=field_map)
    client    = PCClient(ROBOT_IP)

    print("Forbinder til EV3...")
    if not client.connect_to_robot():
        print("Kunne ikke forbinde til robotten. Afslutter.")
        return

    print("Forbundet! Starter kamera-navigation.\n")
    print("=" * 60)

    estimated_heading = None  # Ukendt indtil vi bevaeger os!
    iteration = 0

    try:
        while True:
            iteration += 1
            time.sleep(0.4)

            # --- Find robot og alle bolde ---
            scene = capture_scene(camera, tracker, ball_det)
            if scene is None:
                print("[{}] Kan ikke finde robot eller bold...".format(iteration))
                continue

            _frame, robot, balls = scene
            if not balls:
                print("[{}] Ingen bolde synlige lige nu.".format(iteration))
                continue

            rx, ry = field_map.pixel_to_cm(robot.x, robot.y)
            target = planner.choose_target(balls, (rx, ry))
            if target is None:
                print("[{}] Ingen aktive mål at følge.".format(iteration))
                continue

            bx, by = field_map.pixel_to_cm(target.x, target.y)

            # --- INITIAL KALIBRERING ---
            # Hvis vi ikke kender vinklen, koer fremad for at maale den.
            if estimated_heading is None:
                print("[{}] Ukendt retning. Koerer fremad 10 cm for at kalibrere...".format(iteration))
                client.send_command(encode_command("FORWARD", 10.0))
                client.wait_for_reply()
                time.sleep(0.5)

                result_after = capture_scene(camera, tracker, ball_det)
                if result_after is not None:
                    _frame_after, new_robot, _balls_after = result_after
                    new_rx, new_ry = field_map.pixel_to_cm(new_robot.x, new_robot.y)
                    dx = new_rx - rx
                    dy = new_ry - ry
                    if math.hypot(dx, dy) > 3.0:
                        estimated_heading = math.degrees(math.atan2(dy, dx))
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
                client.send_command(encode_command("COLLECT"))
                client.wait_for_reply()
                time.sleep(0.8)

                if confirm_pickup(camera, tracker, ball_det, planner):
                    picked = planner.confirm_pickup()
                    if picked is not None:
                        print("[{}] Pickup bekræftet: {}".format(iteration, picked.color))
                    estimated_heading = None  # Nulstil efter indsamling (vi ved ikke hvor vi peger)
                else:
                    print("[{}] Pickup ikke bekræftet endnu — beholder nuvaerende maal.".format(iteration))
                continue

            # --- FASE 1: DREJ hvis vinklen er for stor ---
            if abs(turn_angle) > MIN_TURN_DEGREES:
                print("[{}] TURN {}".format(iteration, turn_angle))
                client.send_command(encode_command("TURN", turn_angle))
                client.wait_for_reply()

                estimated_heading += turn_angle
                estimated_heading = (estimated_heading + 180) % 360 - 180
                time.sleep(0.5)
                continue

            # --- FASE 2: KOER FREMAD ---
            step = compute_forward_step(distance)
            print("[{}] FORWARD {}".format(iteration, step))

            client.send_command(encode_command("FORWARD", step))
            client.wait_for_reply()
            time.sleep(0.4)

            # Opdater heading ud fra det nye ryk
            result_after = capture_scene(camera, tracker, ball_det)
            if result_after is not None:
                _frame_after, new_robot, _balls_after = result_after
                new_rx, new_ry = field_map.pixel_to_cm(new_robot.x, new_robot.y)
                dx = new_rx - rx
                dy = new_ry - ry
                if math.hypot(dx, dy) > 3.0:
                    measured_heading = math.degrees(math.atan2(dy, dx))
                    
                    # Udjaevn headingen (80% maal, 20% tidligere estimat) for stabilitet
                    estimated_heading = 0.8 * measured_heading + 0.2 * estimated_heading
                    
                    print("[{}] Heading rettet til: {:.1f}".format(
                        iteration, estimated_heading))

    except KeyboardInterrupt:
        print("\nAfbrudt af bruger.")
    finally:
        client.send_command(encode_command("STOP"))
        client.close()
        camera.release()
        print("Server afsluttet.")


if __name__ == "__main__":
    main()
