import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.planning.strategy import PickupPlanner
from src.vision.ball_detector import BallPosition


class IdentityFieldMap:
    def pixel_to_cm(self, x, y):
        return float(x), float(y)


class PickupPlannerTests(unittest.TestCase):
    def setUp(self):
        self.planner = PickupPlanner(
            IdentityFieldMap(),
            pickup_match_radius_cm=2.0,
            release_after_missing_frames=2,
        )

    def test_orange_is_prioritized_first(self):
        balls = [
            BallPosition(10, 0, "white"),
            BallPosition(30, 0, "orange"),
        ]

        target = self.planner.choose_target(balls, (0.0, 0.0))

        self.assertIsNotNone(target)
        self.assertEqual(target.color, "orange")

    def test_active_target_is_kept_for_a_short_gap(self):
        balls = [
            BallPosition(10, 0, "white"),
            BallPosition(20, 0, "white"),
        ]

        first_target = self.planner.choose_target(balls, (0.0, 0.0))
        self.assertIsNotNone(first_target)
        self.assertEqual((first_target.x, first_target.y), (10, 0))

        second_target = self.planner.choose_target([BallPosition(20, 0, "white")], (0.0, 0.0))
        self.assertIsNotNone(second_target)
        self.assertEqual((second_target.x, second_target.y), (10, 0))

    def test_confirmed_pickup_releases_target(self):
        balls = [
            BallPosition(10, 0, "white"),
            BallPosition(20, 0, "white"),
        ]

        first_target = self.planner.choose_target(balls, (0.0, 0.0))
        self.assertIsNotNone(first_target)
        self.assertEqual((first_target.x, first_target.y), (10, 0))

        picked = self.planner.confirm_pickup()
        self.assertIsNotNone(picked)

        next_target = self.planner.choose_target(balls, (0.0, 0.0))
        self.assertIsNotNone(next_target)
        self.assertEqual((next_target.x, next_target.y), (20, 0))


if __name__ == "__main__":
    unittest.main()
