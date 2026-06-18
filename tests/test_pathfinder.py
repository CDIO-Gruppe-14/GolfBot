import os
import sys
import math
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.planning.pathfinder import find_path, find_path_adaptive

SAFE = 20.0
FIELD_W, FIELD_H = 180, 120


def _min_clearance(path, start, obstacles):
    """Mindste afstand fra hele ruten (start + alle waypoint-segmenter) til
    enhver forhindring, samplet taet langs hvert segment."""
    pts = [start] + list(path)
    worst = float("inf")
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        seg = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(seg))
        for i in range(n + 1):
            t = i / n
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            for ox, oy in obstacles:
                worst = min(worst, math.hypot(x - ox, y - oy))
    return worst


class TestPathfinder(unittest.TestCase):
    def test_clear_line_returns_direct_target(self):
        """Fri bane -> et enkelt waypoint = selve maalet."""
        path = find_path((10, 60), (170, 60), [], FIELD_W, FIELD_H, SAFE)
        self.assertEqual(path, [(170.0, 60.0)])

    def test_no_obstacles_is_direct(self):
        path = find_path((10, 10), (100, 100), [], FIELD_W, FIELD_H, SAFE)
        self.assertEqual(path, [(100.0, 100.0)])

    def test_routes_around_obstacle(self):
        """Forhindring midt mellem start og maal -> ruten skal bue udenom og
        holde sikkerhedsafstand til forhindringen."""
        start = (10, 60)
        goal = (170, 60)
        obstacles = [(90, 60)]  # lige i den direkte linje

        path = find_path(start, goal, obstacles, FIELD_W, FIELD_H, SAFE)

        self.assertIsNotNone(path)
        # Mere end eet waypoint -> der er lagt en omvej
        self.assertGreater(len(path), 1)
        # Sidste waypoint er det praecise maal
        self.assertEqual(path[-1], (float(goal[0]), float(goal[1])))
        # Hele ruten holder (naesten) sikkerhedsafstand til forhindringen
        self.assertGreaterEqual(_min_clearance(path, start, obstacles), SAFE - 1.5)

    def test_robot_radius_widens_obstacle_clearance(self):
        """Med robot_radius skal HELE kroppen gaa fri: ruten holder
        safe_radius + robot_radius fra forhindringen."""
        start = (10, 60)
        goal = (170, 60)
        obstacles = [(90, 60)]
        robot_r = 12.0

        path = find_path(start, goal, obstacles, FIELD_W, FIELD_H, SAFE,
                         robot_radius=robot_r)

        self.assertIsNotNone(path)
        self.assertGreaterEqual(
            _min_clearance(path, start, obstacles), SAFE + robot_r - 1.5)

    def test_robot_radius_keeps_path_off_the_walls(self):
        """Markoer-centret maa ikke komme taettere paa en vaeg end robot_radius,
        ellers rammer kroppen banden."""
        start = (10, 10)
        goal = (170, 110)
        obstacles = [(90, 60)]
        robot_r = 12.0

        path = find_path(start, goal, obstacles, FIELD_W, FIELD_H, SAFE,
                         robot_radius=robot_r)

        self.assertIsNotNone(path)
        # Alle waypoints holder mindst (robot_radius - lille tolerance) fra vaeggene
        for x, y in path[:-1]:  # sidste = praecist maal, kan ligge taet paa kant
            self.assertGreaterEqual(x, robot_r - 1.0)
            self.assertLessEqual(x, FIELD_W - robot_r + 1.0)
            self.assertGreaterEqual(y, robot_r - 1.0)
            self.assertLessEqual(y, FIELD_H - robot_r + 1.0)

    def test_adaptive_degrades_buffer_on_tight_field(self):
        """Stor robot paa traang bane: fuld clearance giver ingen sti, men den
        adaptive variant trapper bufferen ned og finder en rute."""
        start = (20, 60)
        goal = (160, 60)
        obstacles = [(90, 60)]
        big_radius = 23.0  # stor robot

        # Fuld buffer (safe + radius) lukker korridoren -> ingen sti
        full = find_path(start, goal, obstacles, FIELD_W, FIELD_H, SAFE,
                         robot_radius=big_radius)
        self.assertIsNone(full)

        # Adaptiv: finder en sti med reduceret buffer, men beholder kropsradius
        path, used = find_path_adaptive(start, goal, obstacles, FIELD_W, FIELD_H,
                                        SAFE, robot_radius=big_radius)
        self.assertIsNotNone(path)
        self.assertLess(used, SAFE)  # bufferen blev trappet ned
        # Kroppen holdes stadig fri: ruten holder mindst robot_radius fra krydset
        self.assertGreaterEqual(
            _min_clearance(path, start, obstacles), big_radius - 1.5)

    def test_adaptive_returns_none_when_truly_enclosed(self):
        """Indespaerret maal -> adaptiv giver (None, None), saa kalderen springer over."""
        goal = (90, 60)
        ring = [(85, 60), (95, 60), (90, 55), (90, 65)]
        path, used = find_path_adaptive((10, 10), goal, ring, FIELD_W, FIELD_H,
                                        SAFE, robot_radius=12.0)
        self.assertIsNone(path)
        self.assertIsNone(used)

    def test_blocked_goal_returns_none_when_walled_in(self):
        """Maal helt omringet af forhindringer taettere end tolerancen -> ingen sti."""
        goal = (90, 60)
        ring = [(90 - 5, 60), (90 + 5, 60), (90, 60 - 5), (90, 60 + 5)]
        # Start langt vaek; maalet er klemt inde af fire klatter taet paa
        path = find_path((10, 10), goal, ring, FIELD_W, FIELD_H, SAFE)
        # Enten None (umuligt) -- det er den forventede beskyttelse
        self.assertIsNone(path)


if __name__ == "__main__":
    unittest.main()
