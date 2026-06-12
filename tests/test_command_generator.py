import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.planning.command_generator import compute_turn_only


class TestCommandGenerator(unittest.TestCase):
    def test_front_offset_reduces_forward_distance(self):
        turn_angle, distance = compute_turn_only(
            0.0, 0.0, 0.0, 10.0, 0.0, front_offset_cm=4.0
        )

        self.assertEqual(turn_angle, 0.0)
        self.assertEqual(distance, 6.0)

    def test_front_offset_affects_turn_and_distance(self):
        turn_angle, distance = compute_turn_only(
            0.0, 0.0, 0.0, 10.0, 10.0, front_offset_cm=5.0
        )

        self.assertAlmostEqual(turn_angle, 63.4)
        self.assertAlmostEqual(distance, 11.2)


if __name__ == "__main__":
    unittest.main()