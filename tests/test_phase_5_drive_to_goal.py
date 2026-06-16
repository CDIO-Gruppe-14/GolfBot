"""
GolfBot -- Test: Fase 5 (Koer til Maal med forhindrings-undvigelse)
====================================================================
Isoleret hardware-test af KUN Fase 5: robotten koerer fra sin nuvaerende
position til Maal A og skal laegge ruten UDENOM en forhindring.

FORUDSAETNING (saadan saetter du testen op):
  1. Placer det Roede Kryds (forhindringen) MELLEM robotten og Maal A,
     saa den direkte linje til maalet er spaerret.
  2. Sørg for at robottens ArUco-markoer og banens hjoerne-markoerer ses.
  3. Ingen bolde noedvendige -- testen henter ikke bolde, den koerer kun til maal.

Hvad testen goer:
  - Fase 1: detect_obstacles (saetter ctx.obstacles) + detect_robot
  - Fase 5: drive_to_goal(ctx) -- laeser ctx.obstacles og undviger via waypoints

Hold oeje med loggen:
  - "Rute planlagt (N waypoints): ..."  -> undvigelsen er aktiv
  - "Waypoint (x,y) naaet -- N tilbage" -> robotten foelger omvejen
  - At robotten FYSISK koerer udenom krydset og ikke ind i det.

Start:
  python tests/test_phase_5_drive_to_goal.py
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
from src.server.phases.detection import detect_robot, detect_obstacles
from src.server.phases.drive_to_goal import drive_to_goal


def setup():
    """Initialiserer hardware og returnerer GameContext (som server/main.py)."""
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

    field_w, field_h = getattr(field_map, "field_size_cm", (180, 120))
    goal_a_waypoint = compute_waypoint(goal_a_cm[0], goal_a_cm[1], field_w, field_h)

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

    print("\n" + "=" * 60)
    print("GolfBot TEST -- Fase 5 (Koer til Maal med undvigelse)")
    print("=" * 60)

    try:
        # -----------------------------------------------------------
        # Fase 1 (delvis): Detekter forhindringer + robot.
        # detect_obstacles saetter ctx.obstacles, som drive_to_goal laeser.
        # -----------------------------------------------------------
        print("\n>>> FASE 1: DETEKTION (forhindringer + robot) <<<")
        obstacles = detect_obstacles(ctx)
        if obstacles is None:
            print("Forhindrings-detektion fejlede (kamerafejl). Afslutter test.")
            return

        if not obstacles:
            print("ADVARSEL: INGEN forhindringer detekteret!")
            print("  -> Placer det Roede Kryds mellem robot og maal, ellers")
            print("     tester du ikke undvigelsen (robotten koerer bare direkte).")

        if not detect_robot(ctx):
            print("ADVARSEL: Robot ikke fundet ved start -- "
                  "drive_to_goal detekterer igen i sit loop.")

        print("\n[Test] Maal A:      ({:.1f}, {:.1f})".format(
            ctx.goal_a_cm[0], ctx.goal_a_cm[1]))
        print("[Test] Waypoint:    ({:.1f}, {:.1f})".format(
            ctx.goal_a_waypoint[0], ctx.goal_a_waypoint[1]))
        print("[Test] Forhindringer paa ctx: {}".format(ctx.obstacles))

        # -----------------------------------------------------------
        # Fase 5: Koer til maal (eneste fase under test)
        # -----------------------------------------------------------
        print("\n>>> FASE 5: KOER TIL MAAL <<<")
        drive_to_goal(ctx)

        print("\n" + "=" * 60)
        print("TEST AFSLUTTET -- Fase 5 gennemfoert")
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
