import os
import sys
import time
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    ARUCO_DICT,
    PRECISION_TURN_SPEED,
    ROBOT_IP,
    ROBOT_MARKER_ID,
    TURN_SPEED,
)
from src.communication.connection import PCClient
from src.entities.robot import Robot
from src.server.helpers.camera_utils import get_fresh_frame
from src.server.helpers.command_utils import send_and_verify
from src.server.phases.detection import detect_robot
from src.vision.aruco_detector import ArucoDetector
from src.vision.camera import RobotCamera
from src.vision.field_map import FieldMap
from src.vision.robot_tracker import RobotTracker


def _angle_error(actual, expected):
    """Korteste vinkel fra expected til actual i intervallet [-180, 180]."""
    return (actual - expected + 180.0) % 360.0 - 180.0


def _heading_after_turn(start_heading, turn_degrees):
    # Banekoordinaterne har y nedad, saa positiv TURN (hoejre) giver stoerre heading.
    return (start_heading + turn_degrees + 180.0) % 360.0 - 180.0


@unittest.skipUnless(
    os.getenv("RUN_HARDWARE_TESTS") == "1",
    "Hardware-test: saet RUN_HARDWARE_TESTS=1 for at koere den paa banen.",
)
class TestRobotTurnHeading(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.camera = RobotCamera()
        cls.client = PCClient(ROBOT_IP)

        aruco = ArucoDetector(ARUCO_DICT)
        field_map = FieldMap(aruco_detector=aruco)

        frame = get_fresh_frame(cls.camera)
        if frame is None:
            cls.camera.release()
            raise AssertionError("Kameraet kunne ikke levere et frame")

        if field_map.calibrate_from_aruco(frame):
            print("[TurnHeadingTest] ArUco bane-kalibrering brugt.")
        else:
            print("[TurnHeadingTest] Bruger gemt/fallback bane-kalibrering.")

        cls.ctx = SimpleNamespace(
            camera=cls.camera,
            tracker=RobotTracker(aruco, ROBOT_MARKER_ID),
            field_map=field_map,
            robot=Robot(),
        )

        if not cls.client.connect_to_robot():
            cls.camera.release()
            raise AssertionError("Kunne ikke forbinde til EV3")
        cls.ctx.client = cls.client

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

    def _run_turn_heading_test(self, turn_degrees, speed, tolerance_deg):
        settle_sec = float(os.getenv("ROBOT_TURN_SETTLE_SEC", "1.0"))

        self.assertTrue(detect_robot(self.ctx), "Robotten blev ikke fundet foer TURN")
        start_heading = self.ctx.robot.heading
        self.assertIsNotNone(start_heading, "Robot-heading var None foer TURN")

        print(
            "[TurnHeadingTest] Start-heading: {:.1f}. Sender TURN speed {} angle {:.1f}.".format(
                start_heading, speed, turn_degrees
            )
        )
        self.assertIsNotNone(
            send_and_verify(self.client, "TURN", speed, turn_degrees),
            "EV3 svarede ikke DONE paa TURN",
        )

        time.sleep(settle_sec)

        self.assertTrue(detect_robot(self.ctx), "Robotten blev ikke fundet efter TURN")
        actual_heading = self.ctx.robot.heading
        expected_heading = _heading_after_turn(start_heading, turn_degrees)
        error_deg = _angle_error(actual_heading, expected_heading)
        error_percent = abs(error_deg) / abs(turn_degrees) * 100.0

        print(
            "[TurnHeadingTest] TURN {:.1f} speed {}: forventet heading {:.1f}, faktisk {:.1f}, "
            "fejl {:.1f} grader ({:.1f}%)".format(
                turn_degrees,
                speed,
                expected_heading,
                actual_heading,
                error_deg,
                error_percent,
            )
        )

        self.assertLessEqual(
            abs(error_deg),
            tolerance_deg,
            "TURN {:.1f} speed {} fejlede: forventet {:.1f}, faktisk {:.1f}, "
            "fejl {:.1f} grader ({:.1f}%)".format(
                turn_degrees,
                speed,
                expected_heading,
                actual_heading,
                error_deg,
                error_percent,
            ),
        )

    def test_01_robot_turns_90_degrees_and_reports_heading_error_percent(self):
        turn_degrees = float(os.getenv("ROBOT_TURN_90_DEGREES", "90"))
        speed = float(os.getenv("ROBOT_TURN_90_SPEED", str(TURN_SPEED)))
        tolerance_deg = float(os.getenv("ROBOT_TURN_90_TOLERANCE_DEG", "15"))

        self._run_turn_heading_test(turn_degrees, speed, tolerance_deg)

    def test_02_robot_turns_5_degrees_and_reports_heading_error_percent(self):
        turn_degrees = float(os.getenv("ROBOT_TURN_5_DEGREES", "5"))
        speed = float(os.getenv("ROBOT_TURN_5_SPEED", str(PRECISION_TURN_SPEED)))
        tolerance_deg = float(os.getenv("ROBOT_TURN_5_TOLERANCE_DEG", "3"))

        self._run_turn_heading_test(turn_degrees, speed, tolerance_deg)


if __name__ == "__main__":
    unittest.main()
