"""
GolfBot -- Test: Fase 1-3
===========================
Kører fase 1 (detektion), fase 2 (ruteplanlægning) og fase 3 (kør til bold)
i sekvens -- copy-pastet direkte fra server/main.py og cuttet efter fase 3.

Start:
  python tests/test_phase1_to_3.py
"""

import sys
import os

# Gør src-roden og projektroden tilgængelig for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
                    GOAL_A_MARKER_ID, GOAL_B_MARKER_ID)

from src.server.context import GameContext
from src.server.helpers.goal_utils import load_goals, compute_waypoint
from src.server.phases.detection import detect_robot, detect_balls, detect_obstacles
from src.server.phases.route_planner import plan_route
from src.server.phases.drive_to_ball import drive_to_ball


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

    goal_a_waypoint = compute_waypoint(goal_a_cm[0], goal_a_cm[1], offset_cm=20.0)

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
    print("GolfBot TEST -- Fase 1-3")
    print("=" * 60)

    try:
        # -----------------------------------------------------------
        # Fase 1: Detekter (se elementer, gem positioner)
        # -----------------------------------------------------------
        print("\n>>> FASE 1: DETEKTION <<<")
        balls = detect_balls(ctx)
        obstacles = detect_obstacles(ctx)
        if balls is None or obstacles is None:
            print("Detektion fejlede. Afslutter test.")
            return

        # -----------------------------------------------------------
        # Fase 2: Lav rute (prioritetskø)
        # -----------------------------------------------------------
        print("\n>>> FASE 2: RUTEPLANLAEGNING <<<")
        queue = plan_route(ctx, balls, obstacles)

        if not queue:
            print("Ingen bolde fundet. Afslutter test.")
            return

        # -----------------------------------------------------------
        # Fase 3: Kør til første bold (kun én bold for test)
        # -----------------------------------------------------------
        print("\n>>> FASE 3: KOER TIL FOERSTE BOLD <<<")
        ball = queue[0]
        success = drive_to_ball(ctx, ball)
        if success:
            print("\n>>> FASE 3 SUCCES: Naaede bolden! <<<")
        else:
            print("\n>>> FASE 3 FEJL: Kunne ikke naa bolden <<<")

        print("\n" + "=" * 60)
        print("TEST AFSLUTTET -- Fase 1-3 gennemført")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\nAfbrudt af bruger.")
    finally:
        ctx.client.send_command(encode_command("STOP"))
        ctx.client.close()
        ctx.camera.release()
        print("Test afsluttet.")


if __name__ == "__main__":
    main()
