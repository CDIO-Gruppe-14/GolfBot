"""
GolfBot -- GameContext
======================
Delt tilstand for alle faser i serveren.
Samler hardware-referencer og dynamisk navigation-state eet sted,
saa faserne kun behoever en enkelt ctx-parameter.
"""


class GameContext:
    """Central kontekst der deles mellem alle faser i serveren."""

    def __init__(self, camera, tracker, ball_detector, obstacle_detector,
                 field_map, client,
                 goal_a_cm, goal_b_cm, goal_a_waypoint, robot):
        # Hardware / forbindelser (konstante under koersel)
        self.camera = camera
        self.tracker = tracker
        self.ball_detector = ball_detector
        self.obstacle_detector = obstacle_detector
        self.field_map = field_map
        self.client = client

        # Maalkoordinater i cm (konstante under koersel)
        self.goal_a_cm = goal_a_cm
        self.goal_b_cm = goal_b_cm
        self.goal_a_waypoint = goal_a_waypoint

        # Dynamisk navigation-state (opdateres under koersel)
        self.iteration = 0

        # Seneste detekterede forhindringer (cm-punkter). Saettes af
        # detect_obstacles og laeses af drive_to_goal til waypoint-undvigelse.
        self.obstacles = []
        
        # Entities
        self.robot = robot
