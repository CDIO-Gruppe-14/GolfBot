"""
GolfBot -- Fase 2: Ruteplanlaegning
======================================
Beregner optimal raekkefoelge for bolde via prioritetskoee.

Nuvaerende implementering: simpel afstandssortering.
Forberedt til A*-pathfinding via src/planning/pathfinder.py.
"""

import math


class BallQueue:
    """Prioritetskoee over bolde med metoder til at navigere listen."""

    def __init__(self, balls):
        """
        Args:
            balls: liste af (x_cm, y_cm, color) tupler sorteret efter prioritet.
        """
        self._balls = list(balls)
        self._collected = []

    def has_balls(self):
        """Returnerer True hvis der er flere bolde at samle."""
        return len(self._balls) > 0

    def next(self):
        """Returnerer naeste bold som (x, y, color) tuple.
        Fjerner den IKKE fra koeen -- brug mark_collected() efter opsamling."""
        if not self._balls:
            return None
        return self._balls[0]

    def mark_collected(self, ball):
        """Marker en bold som opsamlet og fjern fra koeen."""
        if ball in self._balls:
            self._balls.remove(ball)
            self._collected.append(ball)

    def remaining(self):
        """Antal bolde der mangler at blive samlet."""
        return len(self._balls)

    def collected_count(self):
        """Antal bolde der er samlet op."""
        return len(self._collected)


def plan_route(ctx, detection):
    """
    Fase 2: Beregn optimal raekkefoelge for boldopsamling.

    Nuvaerende implementering:
      - Orange bold foerst (hvis til stede)
      - Derefter sorteret efter afstand fra robot

    Forberedt til fremtidig implementering:
      - A* pathfinding med forhindringer
      - Point-per-km scoring fra strategy.py

    Args:
        ctx: GameContext med robot-position
        detection: DetectionResult fra fase 1

    Returns:
        BallQueue med bolde sorteret efter prioritet
    """
    robot_x = detection.robot_x
    robot_y = detection.robot_y
    balls = list(detection.balls)

    if not balls:
        print("[Ruteplaner] Ingen bolde at planlaegge rute for")
        return BallQueue([])

    # Separer orange og hvide bolde
    orange = [b for b in balls if b[2] == "orange"]
    white = [b for b in balls if b[2] != "orange"]

    # Sorter hvide efter afstand fra robot
    white.sort(key=lambda b: math.hypot(b[0] - robot_x, b[1] - robot_y))

    # Orange foerst, derefter hvide sorteret efter afstand
    sorted_balls = orange + white

    # TODO: Erstat med A*-baseret ruteplanlægning:
    #   from src.planning.pathfinder import AStarPathfinder
    #   pathfinder = AStarPathfinder()
    #   sorted_balls = pathfinder.optimize_order(
    #       sorted_balls, (robot_x, robot_y), detection.obstacles
    #   )

    print("[Ruteplaner] Planlagt raekkefoelge for {} bolde:".format(len(sorted_balls)))
    for i, (bx, by, color) in enumerate(sorted_balls):
        dist = math.hypot(bx - robot_x, by - robot_y)
        print("  {}: ({:.1f}, {:.1f}) {} - {:.1f} cm vaek".format(
            i + 1, bx, by, color, dist))

    return BallQueue(sorted_balls)
