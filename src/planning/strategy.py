"""
GolfBot -- Boldstrategi
========================
Bestemmer raekkefoelgen af bolde baseret paa regler og scoring.

STATUS: Stub med interface -- klar til implementering.

Regler:
  - 11 bolde i alt (1 orange VIP-bold, 10 hvide)
  - Orange bold giver 200 bonuspoint HVIS den afleveres først
  - Maal A (lille, 80mm): 150 point/bold
  - Maal B (stort, 200mm): 100 point/bold
  - 8 minutter til indsamling
  - -50 point per beroering af bane/forhindring

Afhaenger af:
  - src/vision/ball_detector.py (BallPosition)
"""

import math


class BoldStrategi:
    """Bestemmer raekkefoelge af bolde baseret paa afstand og scoring."""

    def __init__(self, pathfinder=None):
        """
        Args:
            pathfinder: AStarPathfinder instans (valgfri, bruges til ruteberegning)
        """
        self.pathfinder = pathfinder

    def prioritize(self, balls, robot_pos, goal_pos, obstacles=None):
        """
        Sorter bolde efter prioritet.

        Nuvaerende implementering:
          - Orange bold foerst
          - Derefter sorteret efter afstand

        Fremtidig implementering:
          - Orange foerst (200 bonuspoint)
          - Derefter point-per-km scoring
          - A*-rutelaengde i stedet for euklidisk afstand

        Args:
            balls: Liste af (x, y, color) bold-positioner
            robot_pos: (x, y) robotposition i cm
            goal_pos: (x, y) maalposition i cm
            obstacles: Liste af forhindringer (til A*)

        Returns:
            Sorteret liste af bolde.
        """
        if not balls:
            return []

        orange = [b for b in balls if b[2] == "orange"]
        white = [b for b in balls if b[2] != "orange"]

        # Sorter hvide efter afstand fra robot
        rx, ry = robot_pos
        white.sort(key=lambda b: math.hypot(b[0] - rx, b[1] - ry))

        return orange + white
