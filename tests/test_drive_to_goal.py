import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    ARUCO_DICT,
    CAMERA_INDEX,
    GOAL_A_MARKER_ID,
    GOAL_B_MARKER_ID,
    ROBOT_FRONT_CM,
    ROBOT_IP,
    ROBOT_MARKER_ID,
)
from src.communication.connection import PCClient
from src.entities.robot import Robot
from src.planning.command_generator import compute_distance, compute_turn_only
from src.server.context import GameContext
from src.server.helpers.camera_utils import get_fresh_frame
from src.server.helpers.command_utils import send_and_verify
from src.server.helpers.goal_utils import compute_waypoint, load_goals
from src.server.phases.detection import detect_obstacles, detect_robot
from src.server.phases.drive_to_goal import drive_to_goal
from src.vision.aruco_detector import ArucoDetector
from src.vision.ball_detector import BallDetector
from src.vision.camera import RobotCamera
from src.vision.color_detector import ColorDetector
from src.vision.field_map import FieldMap
from src.vision.goal_detector import GoalDetector
from src.vision.obstacle_detector import ObstacleDetector
from src.vision.robot_tracker import RobotTracker


def _distance_to_goal_reference(ctx):
    """Maal samme front-til-maal distance som drive_to_goal navigerer efter."""
    return compute_distance(
        ctx.robot.x,
        ctx.robot.y,
        ctx.goal_a_cm[0],
        ctx.goal_a_cm[1],
        ctx.robot.heading,
        front_offset_cm=ROBOT_FRONT_CM,
    )


def _setup_context():
    """Initialiser hardware og returner GameContext til fase 5-testen."""
    camera = RobotCamera()
    aruco = ArucoDetector(ARUCO_DICT)
    tracker = RobotTracker(aruco, ROBOT_MARKER_ID)

    detector = ColorDetector()
    loaded = detector.load_all_profiles()
    print("[DriveToGoalTest] Indlaedte farveprofiler: {}".format(loaded))

    field_map = FieldMap(aruco_detector=aruco)
    ball_det = BallDetector(detector, field_map)
    obstacle_det = ObstacleDetector(detector, field_map)

    client = PCClient(ROBOT_IP)
    print("[DriveToGoalTest] Forbinder til EV3...")
    if not client.connect_to_robot():
        camera.release()
        raise AssertionError("Kunne ikke forbinde til EV3")
    print("[DriveToGoalTest] Forbundet!")

    frame = get_fresh_frame(camera)
    if frame is None:
        client.close()
        camera.release()
        raise AssertionError("Kameraet kunne ikke levere et frame")

    if field_map.calibrate_from_aruco(frame):
        print("[DriveToGoalTest] ArUco bane-kalibrering brugt.")
    else:
        print("[DriveToGoalTest] Bruger gemt/fallback bane-kalibrering.")

    goal_det = GoalDetector(aruco, field_map, GOAL_A_MARKER_ID, GOAL_B_MARKER_ID)
    goal_a_aruco, goal_b_aruco = goal_det.detect_goals(frame)

    goal_a_fallback, goal_b_fallback = load_goals()
    goal_a_cm = goal_a_aruco if goal_a_aruco else goal_a_fallback
    goal_b_cm = goal_b_aruco if goal_b_aruco else goal_b_fallback

    if goal_a_aruco:
        print("[DriveToGoalTest] Maal A fundet via ArUco: {}".format(goal_a_cm))
    else:
        print("[DriveToGoalTest] Maal A fra fallback: {}".format(goal_a_cm))

    if goal_b_aruco:
        print("[DriveToGoalTest] Maal B fundet via ArUco: {}".format(goal_b_cm))
    else:
        print("[DriveToGoalTest] Maal B fra fallback: {}".format(goal_b_cm))

    field_w, field_h = getattr(field_map, "field_size_cm", (180, 120))
    goal_a_waypoint = compute_waypoint(goal_a_cm[0], goal_a_cm[1], field_w, field_h)
    print("[DriveToGoalTest] Maal A waypoint: {}".format(goal_a_waypoint))

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
        robot=Robot(),
    )


@unittest.skipUnless(
    os.getenv("RUN_HARDWARE_TESTS") == "1",
    "Hardware-test: saet RUN_HARDWARE_TESTS=1 for at koere den paa banen.",
)
class TestDriveToGoal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = _setup_context()
        cls.client = cls.ctx.client
        cls.camera = cls.ctx.camera

    @classmethod
    def tearDownClass(cls):
        try:
            client = getattr(cls, "client", None)
            if (
                os.getenv("ROBOT_STOP_AFTER_TEST") == "1"
                and client
                and client.client_socket
            ):
                send_and_verify(client, "STOP")
        finally:
            client = getattr(cls, "client", None)
            if client:
                client.close()
            camera = getattr(cls, "camera", None)
            if camera:
                camera.release()

    def test_drive_to_goal_phase_5_reaches_goal_and_faces_it(self):
        ctx = self.ctx
        obstacles = detect_obstacles(ctx)


        self.assertTrue(
            detect_robot(ctx),
            "Robotten blev ikke fundet foer fase 5. Tjek robotmarkoer ID {} "
            "og kamera index {}.".format(ROBOT_MARKER_ID, CAMERA_INDEX),
        )

        print("[DriveToGoalTest] Maal A: {}".format(ctx.goal_a_cm))
        print("[DriveToGoalTest] Waypoint: {}".format(ctx.goal_a_waypoint))

        drive_to_goal(ctx, obstacles)

        self.assertTrue(
            detect_robot(ctx),
            "Robotten blev ikke fundet efter fase 5. Kan ikke validere slutpose.",
        )

        final_distance_cm = _distance_to_goal_reference(ctx)
        heading_error_deg = compute_turn_only(
            ctx.robot.x,
            ctx.robot.y,
            ctx.robot.heading,
            ctx.goal_a_cm[0],
            ctx.goal_a_cm[1],
        )
        heading_tolerance_deg = float(
            os.getenv("ROBOT_GOAL_HEADING_TOLERANCE_DEG", "10")
        )

        print(
            "[DriveToGoalTest] Slutposition: ({:.1f}, {:.1f}), heading {:.1f}".format(
                ctx.robot.x, ctx.robot.y, ctx.robot.heading
            )
        )
        print(
            "[DriveToGoalTest] Slutafstand til maal: {:.1f} cm".format(
                final_distance_cm
            )
        )
        print(
            "[DriveToGoalTest] Heading-fejl mod maal: {:.1f} grader".format(
                heading_error_deg
            )
        )

        self.assertLess(
            final_distance_cm,
            8.0,
            "Robotten endte {:.1f} cm fra maal A; forventet < 8.0 cm".format(
                final_distance_cm
            ),
        )
        self.assertLessEqual(
            abs(heading_error_deg),
            heading_tolerance_deg,
            "Robotten pegede {:.1f} grader ved siden af maal A; tolerance er {:.1f} grader".format(
                heading_error_deg, heading_tolerance_deg
            ),
        )


if __name__ == "__main__":
    unittest.main()
