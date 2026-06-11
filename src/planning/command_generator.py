import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import MAX_STEP_CM, ROBOT_FRONT_OFFSET_CM


def _front_position(robot_x, robot_y, robot_heading, front_offset_cm):
    if robot_heading is None or front_offset_cm <= 0:
        return robot_x, robot_y

    heading_rad = math.radians(robot_heading)
    front_x = robot_x + math.cos(heading_rad) * front_offset_cm
    front_y = robot_y + math.sin(heading_rad) * front_offset_cm
    return front_x, front_y


def compute_turn_and_distance(robot_x, robot_y, robot_heading, target_x, target_y,
                              front_offset_cm=ROBOT_FRONT_OFFSET_CM):
    """Beregn drejning og afstand fra robotfronten til et maaalpunkt."""
    front_x, front_y = _front_position(robot_x, robot_y, robot_heading, front_offset_cm)

    dx = target_x - front_x
    dy = target_y - front_y

    target_angle = math.degrees(math.atan2(dy, dx))
    distance = math.hypot(dx, dy)

    if robot_heading is None:
        turn_angle = target_angle
    else:
        turn_angle = (target_angle - robot_heading + 180) % 360 - 180

    return round(turn_angle, 1), round(distance, 1)


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


def compute_turn_only(robot_x, robot_y, robot_heading, ball_x, ball_y,
                      front_offset_cm=ROBOT_FRONT_OFFSET_CM):
    """
    Beregn KUN drejning. Returnerer (turn_angle, distance).
    Kalder IKKE forward -- det goer serveren separat efter re-evaluering.
    """
    return compute_turn_and_distance(
        robot_x,
        robot_y,
        robot_heading,
        ball_x,
        ball_y,
        front_offset_cm=front_offset_cm,
    )


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


def calculate_approach_point(ball_x, ball_y, obstacle_x, obstacle_y, approach_dist_cm):
    """
    Beregner et punkt, som robotten skal køre til FØR den samler bolden op.
    Sikrer at robotten angriber bolden vinkelret i forhold til forhindringen.
    """
    dx = ball_x - obstacle_x
    dy = ball_y - obstacle_y
    
    distance = math.hypot(dx, dy)
    
    if distance == 0:
        return ball_x, ball_y # Sikkerhedstjek
        
    dir_x = dx / distance
    dir_y = dy / distance
    
    approach_x = ball_x + (dir_x * approach_dist_cm)
    approach_y = ball_y + (dir_y * approach_dist_cm)
    
    return round(approach_x, 1), round(approach_y, 1)
