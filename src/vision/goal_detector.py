class GoalDetector:
    """Finder mål A/B via ArUco-markører."""
    
    def __init__(self, aruco_detector, field_map,
                 goal_a_id=10, goal_b_id=11):
        self.aruco = aruco_detector
        self.field_map = field_map
        self.goal_a_id = goal_a_id
        self.goal_b_id = goal_b_id
    
    def detect_goals(self, frame, detections=None) -> tuple:
        """Returnerer (goal_a_cm, goal_b_cm). None for ikke-fundne."""
        if detections is None:
            detections = self.aruco.detect(frame)
        
        goal_a = self._find_goal(detections, self.goal_a_id)
        goal_b = self._find_goal(detections, self.goal_b_id)
        return goal_a, goal_b
    
    def _find_goal(self, detections, marker_id):
        if marker_id not in detections:
            return None
        px, py = self.aruco.get_center(detections[marker_id])
        return self.field_map.pixel_to_cm(px, py)
