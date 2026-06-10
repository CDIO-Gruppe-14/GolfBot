import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import MAX_STEP_CM


def compute_angle_to_ball(robot_x, robot_y, ball_x, ball_y):
    """Beregn vinkel fra robot til bold i grader (0 = oest, 90 = nord)."""
    dx = ball_x - robot_x
    dy = ball_y - robot_y
    return math.degrees(math.atan2(dy, dx))


def compute_distance(robot_x, robot_y, ball_x, ball_y):
    """Beregn afstand fra robot til bold i cm."""
    dx = ball_x - robot_x
    dy = ball_y - robot_y
    return math.hypot(dx, dy)


def compute_turn_only(robot_x, robot_y, robot_heading, ball_x, ball_y):
    """
    Beregn KUN drejning. Returnerer (turn_angle, distance).
    Kalder IKKE forward -- det goer serveren separat efter re-evaluering.
    """
    target_angle = compute_angle_to_ball(robot_x, robot_y, ball_x, ball_y)
    distance = compute_distance(robot_x, robot_y, ball_x, ball_y)

    # Beregn mindste drejning (-180 til +180)
    turn_angle = (target_angle - robot_heading + 180) % 360 - 180

    return round(turn_angle, 1), round(distance, 1)


def compute_forward_step(distance):
    """
    Begraens fremadkoersel til MAX_STEP_CM for at undgaa overshoot.
    Sikr desuden at vi ikke kører helt frem til bolden i et normalt step,
    så vi tvinger præcisions-tilnærmelsen i main.py til at tage over.
    """
    from config import APPROACH_DISTANCE_CM
    
    if distance <= APPROACH_DISTANCE_CM:
        return round(distance, 1)
        
    # Kør kun indtil vi er lige i kanten af præcisions-zonen
    safe_dist = distance - (APPROACH_DISTANCE_CM - 1.0)
    return round(min(safe_dist, MAX_STEP_CM), 1)
