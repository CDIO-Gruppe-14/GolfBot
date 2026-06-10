import unittest
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.server.phases.detection import detect_balls, detect_obstacals, detect_robot
from src.vision.ball_detector import BallDetector
from src.vision.camera import RobotCamera
from src.vision.color_detector import ColorDetector
from src.vision.field_map import FieldMap
from src.vision.robot_tracker import RobotTracker


class TestPhase1Detection(unittest.TestCase):
    def test_phase1_with_camera(self):
        camera = RobotCamera()
        try:
            frame = camera.get_frame()
            if frame is None:
                self.fail("Kameraet kunne ikke levere et frame")

            detector = ColorDetector()
            loaded_profiles = detector.load_all_profiles()
            if not loaded_profiles:
                self.fail("Ingen farveprofiler blev indlæst fra color_profiles/. Kør kalibrering først.")

            ctx = SimpleNamespace(
                camera=camera,
                tracker=RobotTracker(detector),
                ball_detector=BallDetector(detector),
                field_map=FieldMap(),
                estimated_heading=None,
            )

            robot = detect_robot(ctx)
            balls = detect_balls(ctx)
            obstacles = detect_obstacals(ctx)

            print("\n--- Phase 1 resultater ---")
            print(f"Robot: {robot}")
            print(f"Bolde fundet: {len(balls)}")
            for ball in balls:
                print(f"  {ball}")
            print(f"Forhindringer fundet: {len(obstacles)}")

            self.assertIsNotNone(robot)
            self.assertIsInstance(balls, list)
            self.assertIsInstance(obstacles, list)

        finally:
            camera.release()


if __name__ == "__main__":
    unittest.main()