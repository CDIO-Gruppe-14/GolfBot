import os
import sys
from collections import deque
from types import SimpleNamespace
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.entities.ball import Ball
from src.server.phases.route_planner import plan_route


class TestRoutePlanner(unittest.TestCase):
    def test_plan_route_returns_standard_deque(self):
        ctx = SimpleNamespace(
            robot=SimpleNamespace(x=0.0, y=0.0),
            field_map=SimpleNamespace(field_size_cm=(180, 120)),
        )
        balls = [
            Ball(30, 30, "white"),
            Ball(10, 10, "orange"),
            Ball(20, 20, "white"),
        ]

        queue = plan_route(ctx, balls, [])

        self.assertIsInstance(queue, deque)
        self.assertTrue(queue)
        self.assertCountEqual(list(queue), balls)

        first_ball = queue[0]
        removed_ball = queue.popleft()
        self.assertEqual(first_ball, removed_ball)
        self.assertEqual(len(queue), 2)


if __name__ == "__main__":
    unittest.main()