"""
GolfBot -- Server Orchestrator
=================================
Ren main der følger flows i faser:

  1. Detekter      (se elementer, gem positioner)
  2. Lav rute      (prioritetskoee, forberedt til A*)
  while bold != null:
      3. Koer til bold  (koriger, stop foran med rigtig vinkel)
      4. Opsamling      (transportbaand, koer roligt frem, marker opsamlet)
  5. Koer til maal  (waypoint + direkte)
  6. Aflevering     (transportbaand i reverse)
  7. Ny detektion   (if bolde == null: End, else: lav ny rute)

Start:
  python src/server/main.py
"""

import sys
import os

# Goer src-roden og projektroden tilgaengelig for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.vision.camera import RobotCamera
from src.vision.color_detector import ColorDetector
from src.vision.robot_tracker import RobotTracker
from src.vision.ball_detector import BallDetector
from src.vision.field_map import FieldMap
from src.communication.connection import PCClient
from src.communication.protocol import encode_command

from config import ROBOT_IP, MARKER_COLOR, MARKER_COLOR_BACK

from src.server.context import GameContext
from src.server.helpers.goal_utils import load_goals, compute_waypoint
from src.server.phases.detection import detect_all
from src.server.phases.route_planner import plan_route
from src.server.phases.drive_to_ball import drive_to_ball
from src.server.phases.ball_collection import collect_ball
from src.server.phases.drive_to_goal import drive_to_goal
from src.server.phases.delivery import deliver_balls


def setup():
    """Initialiserer hardware og returnerer GameContext."""
    camera = RobotCamera()
    detector = ColorDetector()
    loaded = detector.load_all_profiles()
    print("Indlaedte farveprofiler: {}".format(loaded))

    tracker = RobotTracker(detector, marker_color=MARKER_COLOR,
                           marker_color_back=MARKER_COLOR_BACK)
    ball_det = BallDetector(detector)
    field_map = FieldMap()
    client = PCClient(ROBOT_IP)

    print("Forbinder til EV3...")
    if not client.connect_to_robot():
        print("Kunne ikke forbinde til robotten. Afslutter.")
        return None

    print("Forbundet!")

    # Indlaes maalkoordinater
    goal_a_cm, goal_b_cm = load_goals()
    goal_a_waypoint = compute_waypoint(goal_a_cm[0], goal_a_cm[1], offset_cm=20.0)

    return GameContext(
        camera=camera,
        tracker=tracker,
        ball_detector=ball_det,
        field_map=field_map,
        client=client,
        goal_a_cm=goal_a_cm,
        goal_b_cm=goal_b_cm,
        goal_a_waypoint=goal_a_waypoint
    )


def main():
    ctx = setup()
    if ctx is None:
        return

    print("\n" + "=" * 60)
    print("GolfBot startet -- foelger whiteboard-flow")
    print("=" * 60)

    try:
        while True:
            # -----------------------------------------------------------
            # Fase 1: Detekter (se elementer, gem positioner)
            # -----------------------------------------------------------
            print("\n>>> FASE 1: DETEKTION <<<")
            detection = detect_all(ctx)
            if detection is None:
                print("Detektion fejlede. Proever igen...")
                continue

            # -----------------------------------------------------------
            # Fase 2: Lav rute (prioritetskoee)
            # -----------------------------------------------------------
            print("\n>>> FASE 2: RUTEPLANLAEGNING <<<")
            queue = plan_route(ctx, detection)

            if not queue.has_balls():
                print("Ingen bolde fundet. Afslutter.")
                break

            # -----------------------------------------------------------
            # Fase 3 + 4: Opsam alle bolde (while bold != null)
            # -----------------------------------------------------------
            print("\n>>> FASE 3+4: OPSAMLING AF {} BOLDE <<<".format(
                queue.remaining()))

            while queue.has_balls():
                ball = queue.next()

                # Fase 3: Koer til bold
                success = drive_to_ball(ctx, ball)
                if not success:
                    print("Koersel til bold fejlede. Springer over.")
                    queue.mark_collected(ball)
                    continue

                # Fase 4: Opsam bold
                collect_ball(ctx, ball, queue)

            # -----------------------------------------------------------
            # Fase 5: Koer til maal
            # -----------------------------------------------------------
            print("\n>>> FASE 5: KOER TIL MAAL <<<")
            drive_to_goal(ctx)

            # -----------------------------------------------------------
            # Fase 6: Aflevering
            # -----------------------------------------------------------
            print("\n>>> FASE 6: AFLEVERING <<<")
            deliver_balls(ctx)

            # -----------------------------------------------------------
            # Fase 7: Detekter for ny runde
            # -----------------------------------------------------------
            print("\n>>> FASE 7: NY DETEKTION <<<")
            detection = detect_all(ctx)
            if detection is None or not detection.has_balls():
                print("Alle bolde samlet op. Afslutter.")
                break

            print("{} bolde tilbage -- starter ny runde!".format(
                len(detection.balls)))
            # Loop fortsaetter -> ny rute fra fase 2

    except KeyboardInterrupt:
        print("\nAfbrudt af bruger.")
    finally:
        ctx.client.send_command(encode_command("STOP"))
        ctx.client.close()
        ctx.camera.release()
        print("Server afsluttet.")


if __name__ == "__main__":
    main()
