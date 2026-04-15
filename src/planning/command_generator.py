import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config import MIN_TURN_DEGREES, MIN_DISTANCE_CM

def compute_navigation(robot_x_cm, robot_y_cm, robot_heading_deg,
                       ball_x_cm, ball_y_cm) -> list[tuple[str, float]]:
    """
    Beregner de nødvendige kommandoer for at køre fra robotten til bolden.
    
    :param robot_x_cm: Robottens x-koordinat i cm
    :param robot_y_cm: Robottens y-koordinat i cm
    :param robot_heading_deg: Robottens nuværende retning i grader (gyro)
    :param ball_x_cm: Boldens x-koordinat i cm
    :param ball_y_cm: Boldens y-koordinat i cm
    :return: En liste af (kommando, værdi) par (f.eks. [("TURN", -35.2), ("FORWARD", 42.1)])
    """
    dx = ball_x_cm - robot_x_cm
    dy = ball_y_cm - robot_y_cm
    
    # Målvinkel (i forhold til koordinatsystemet)
    target_angle = math.degrees(math.atan2(dy, dx))
    
    # Hvor meget skal robotten dreje?
    turn_angle = (target_angle - robot_heading_deg + 180) % 360 - 180

    # Afstand i cm
    distance = math.hypot(dx, dy)

    commands = []
    
    # Dead-zone: undgå micro-drej (under MIN_TURN_DEGREES grader)
    if abs(turn_angle) > MIN_TURN_DEGREES:
        commands.append(("TURN", round(turn_angle, 1)))
        
    # Dead-zone: stop hvis vi er tæt nok på bolden (under MIN_DISTANCE_CM cm)
    if distance > MIN_DISTANCE_CM:
        commands.append(("FORWARD", round(distance, 1)))
        
    return commands
