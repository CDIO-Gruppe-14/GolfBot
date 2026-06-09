"""
GolfBot -- A* Pathfinder
=========================
A* ruteplanlægning med forhindringer.

STATUS: Stub -- klar til implementering.
Nuvaerende implementering returnerer direkte linje (ingen obstacle avoidance).

Afhænger af:
  - src/vision/obstacle_detector.py  (ObstacleZone -- endnu ikke implementeret)
  - src/vision/field_map.py          (bane-dimensioner)
"""

import math


class AStarPathfinder:
    """A* pathfinder med support for forhindringer paa banen."""

    def __init__(self, field_width=180.0, field_height=120.0, grid_resolution=5.0):
        """
        Args:
            field_width: Banens bredde i cm
            field_height: Banens hoejde i cm
            grid_resolution: Stoerrelse paa grid-celler i cm (mindre = mere praecis)
        """
        self.field_width = field_width
        self.field_height = field_height
        self.grid_resolution = grid_resolution

    def find_path(self, start, goal, obstacles=None):
        """
        Find korteste vej fra start til goal med A*.

        Args:
            start: (x, y) startposition i cm
            goal: (x, y) maalposition i cm
            obstacles: Liste af (x, y, radius) forhindringer i cm

        Returns:
            Liste af (x, y) waypoints fra start til goal.
            Nuvaerende stub: returnerer direkte linje.

        TODO: Implementer A*-algoritmen:
          1. Opret grid over banen baseret paa grid_resolution
          2. Marker forhindringer (+ sikkerhedsmargin) som ikke-fremkommelige
          3. Koer A* fra start-celle til goal-celle
          4. Konverter celle-sti til cm-waypoints
          5. Optimer waypoints (fjern unodvendige mellemstop)
        """
        return [start, goal]

    def path_cost(self, start, goal, obstacles=None):
        """Beregn estimeret cost (afstand) for ruten.

        Nuvaerende stub: returnerer euklidisk afstand.
        Fremtidig impl: returnerer faktisk A*-rutelaengde.
        """
        return math.hypot(goal[0] - start[0], goal[1] - start[1])

    def optimize_order(self, balls, robot_pos, obstacles=None):
        """
        Sorter bolde i optimal opsamlingsraekkefoelge baseret paa A*-ruter.

        Args:
            balls: Liste af (x, y, color) bold-positioner
            robot_pos: (x, y) robotposition
            obstacles: Liste af forhindringer

        Returns:
            Sorteret liste af bolde.

        TODO: Implementer TSP-lignende optimering:
          1. Beregn A*-cost mellem alle par af bolde + robot
          2. Brug nearest-neighbor eller 2-opt til at finde billig raekkefoelge
          3. Vaegt orange-bonus (200 point) ind i cost-beregningen
        """
        return list(balls)
