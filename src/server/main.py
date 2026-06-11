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

from src.entities.robot import Robot

from src.vision.camera import RobotCamera
from src.vision.color_detector import ColorDetector
from src.vision.robot_tracker import RobotTracker
from src.vision.ball_detector import BallDetector
from src.vision.obstacle_detector import ObstacleDetector
from src.vision.field_map import FieldMap
from src.vision.aruco_detector import ArucoDetector
from src.vision.goal_detector import GoalDetector
from src.communication.connection import PCClient
from src.communication.protocol import encode_command

from config import (ROBOT_IP, ARUCO_DICT, ROBOT_MARKER_ID,
                    GOAL_A_MARKER_ID, GOAL_B_MARKER_ID, DELIVER_DISTANCE_CM)

from src.server.context import GameContext
from src.server.helpers.goal_utils import load_goals, compute_waypoint
from src.server.phases.detection import detect_robot, detect_balls, detect_obstacles
from src.server.phases.route_planner import plan_route
from src.server.phases.drive_to_ball import drive_to_ball
from src.server.phases.ball_collection import collect_ball
from src.server.phases.drive_to_goal import drive_to_goal
from src.server.phases.delivery import deliver_balls


def setup():
    """Initialiserer hardware og returnerer GameContext."""
    camera = RobotCamera()
    # ArUco
    aruco = ArucoDetector(ARUCO_DICT)
    tracker = RobotTracker(aruco, ROBOT_MARKER_ID)

    # HSV-farvedetektion (bevares for bolde)
    detector = ColorDetector()
    loaded = detector.load_all_profiles()
    print("Indlaedte farveprofiler: {}".format(loaded))

    # Banekalibrering via ArUco (definerer ROI for bold-/forhindringsdetektion)
    field_map = FieldMap(aruco_detector=aruco)
    ball_det = BallDetector(detector, field_map)
    obstacle_det = ObstacleDetector(detector, field_map)

    client = PCClient(ROBOT_IP)
    
    print("Forbinder til EV3...")
    if not client.connect_to_robot():
        print("Kunne ikke forbinde til robotten. Afslutter.")
        return None
    print("Forbundet!")

    # Tag et test-billede til kalibrering
    frame = camera.get_frame()
    if frame is not None:
        if not field_map.calibrate_from_aruco(frame):
            print("ArUco bane-kalibrering fejlede — bruger fallback")
        else:
            print("ArUco bane-kalibrering succes!")

    # Mål via ArUco med fallback
    goal_det = GoalDetector(aruco, field_map, GOAL_A_MARKER_ID, GOAL_B_MARKER_ID)
    goal_a_aruco, goal_b_aruco = goal_det.detect_goals(frame) if frame is not None else (None, None)
    
    goal_a_fallback, goal_b_fallback = load_goals()
    goal_a_cm = goal_a_aruco if goal_a_aruco else goal_a_fallback
    goal_b_cm = goal_b_aruco if goal_b_aruco else goal_b_fallback
    
    if goal_a_aruco: print(f"Mål A fundet via ArUco: {goal_a_cm}")
    if goal_b_aruco: print(f"Mål B fundet via ArUco: {goal_b_cm}")

    goal_a_waypoint = compute_waypoint(goal_a_cm[0], goal_a_cm[1], DELIVER_DISTANCE_CM)

    return GameContext(
        camera=camera,
        tracker=tracker,
        ball_detector=ball_det,
        obstacle_detector=obstacle_det,
        field_map=field_map,
        client=client,
        goal_a_cm=goal_a_cm,
        goal_b_cm=goal_b_cm,
        goal_a_waypoint=goal_a_waypoint,
        robot=Robot()
    )


def main():
    ctx = setup()
    if ctx is None:
        return

    if not detect_robot(ctx):
        print("ADVARSEL: Robot ikke fundet ved start -- fortsaetter (faserne detekterer igen)")

    print("\n" + "=" * 60)
    print("GolfBot startet -- foelger whiteboard-flow")
    print("=" * 60)

    try:
        while True:
            # -----------------------------------------------------------
            # Fase 1: Detekter (se elementer, gem positioner)
            # -----------------------------------------------------------
            print("\n>>> FASE 1: DETEKTION <<<")
            balls = detect_balls(ctx)
            obstacles = detect_obstacles(ctx)
            if balls is None or obstacles is None:
                print("Detektion fejlede. Proever igen...")
                continue

            # -----------------------------------------------------------
            # Fase 2: Lav rute (prioritetskoee)
            # -----------------------------------------------------------
            print("\n>>> FASE 2: RUTEPLANLAEGNING <<<")
            queue = plan_route(ctx, balls, obstacles)

            if not queue:
                print("Ingen bolde fundet. Afslutter.")
                break

            # -----------------------------------------------------------
            # Fase 3 + 4: Opsam alle bolde (while bold != null)
            # -----------------------------------------------------------
            print("\n>>> FASE 3+4: OPSAMLING AF {} BOLDE <<<".format(
                len(queue)))

            while queue:
                ball = queue[0]

                # Fase 3: Koer til bold
                success = drive_to_ball(ctx, ball, obstacles)
                if not success:
                    print("Koersel til bold fejlede. Springer over.")
                    queue.popleft()
                    continue

                # Fase 4: Opsam bold
                collect_ball(ctx, ball)
                queue.popleft()

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
            balls = detect_balls(ctx)
            if balls is None or not balls:
                print("Alle bolde samlet op. Afslutter.")
                break

            print("{} bolde tilbage -- starter ny runde!".format(len(balls)))
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
