import os
import sys
import time
import math
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import ARUCO_DICT, ROBOT_IP, ROBOT_MARKER_ID
from src.communication.connection import PCClient
from src.entities.robot import Robot
from src.server.helpers.camera_utils import get_fresh_frame
from src.server.helpers.command_utils import send_and_verify
from src.server.phases.detection import detect_robot
from src.vision.aruco_detector import ArucoDetector
from src.vision.camera import RobotCamera
from src.vision.field_map import FieldMap
from src.vision.robot_tracker import RobotTracker


def _distance(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


@unittest.skipUnless(
    os.getenv("RUN_HARDWARE_TESTS") == "1",
    "Hardware-test: saet RUN_HARDWARE_TESTS=1 for at koere den paa banen.",
)
class TestRobotDriveStraight(unittest.TestCase):
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
            print("[DriveStraightTest] ArUco bane-kalibrering brugt.")
        else:
            print("[DriveStraightTest] Bruger gemt/fallback bane-kalibrering.")

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

    def _run_drive_straight_test(self, distance_cm, tolerance_cm):
        settle_sec = float(os.getenv("ROBOT_DRIVE_SETTLE_SEC", "2.0"))

        self.assertTrue(detect_robot(self.ctx), "Robotten blev ikke fundet foer FORWARD")
        start_x = self.ctx.robot.x
        start_y = self.ctx.robot.y
        self.assertIsNotNone(start_x, "Robot-x var None foer FORWARD")
        self.assertIsNotNone(start_y, "Robot-y var None foer FORWARD")

        print(
            "[DriveStraightTest] Start-position: ({:.1f}, {:.1f}). Sender FORWARD {:.1f}.".format(
                start_x, start_y, distance_cm
            )
        )
        self.assertIsNotNone(
            send_and_verify(self.client, "FORWARD", distance_cm),
            "EV3 svarede ikke DONE paa FORWARD",
        )

        time.sleep(settle_sec)

        self.assertTrue(detect_robot(self.ctx), "Robotten blev ikke fundet efter FORWARD")
        end_x = self.ctx.robot.x
        end_y = self.ctx.robot.y
        
        actual_distance = _distance(start_x, start_y, end_x, end_y)
        error_cm = actual_distance - distance_cm
        error_percent = abs(error_cm) / abs(distance_cm) * 100.0 if distance_cm != 0 else 0.0

        print(
            "[DriveStraightTest] FORWARD {:.1f}: forventet afstand {:.1f}, faktisk {:.1f}, "
            "fejl {:.1f} cm ({:.1f}%)".format(
                distance_cm,
                distance_cm,
                actual_distance,
                error_cm,
                error_percent,
            )
        )

        self.assertLessEqual(
            abs(error_cm),
            tolerance_cm,
            "FORWARD {:.1f} fejlede: forventet {:.1f}, faktisk {:.1f}, "
            "fejl {:.1f} cm ({:.1f}%)".format(
                distance_cm,
                distance_cm,
                actual_distance,
                error_cm,
                error_percent,
            ),
        )

    def test_01_robot_drives_10_cm_and_reports_distance_error_percent(self):
        distance_cm = float(os.getenv("ROBOT_DRIVE_10_CM", "10.0"))
        tolerance_cm = float(os.getenv("ROBOT_DRIVE_10_TOLERANCE_CM", "2.0"))

        self._run_drive_straight_test(distance_cm, tolerance_cm)

    def test_02_robot_drives_20_cm_and_reports_distance_error_percent(self):
        distance_cm = float(os.getenv("ROBOT_DRIVE_20_CM", "20.0"))
        tolerance_cm = float(os.getenv("ROBOT_DRIVE_20_TOLERANCE_CM", "3.0"))

        self._run_drive_straight_test(distance_cm, tolerance_cm)


if __name__ == "__main__":
    unittest.main()