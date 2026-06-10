from dataclasses import dataclass
from typing import Optional
from src.entities.robot import Robot


@dataclass
class RobotPosition:
    x: float           # pixels (markør-center)
    y: float           # pixels (markør-center)
    heading_deg: float # grader, direkte fra markør-orientering


class RobotTracker:
    def __init__(self, aruco_detector, robot_marker_id=42):
        self.aruco = aruco_detector
        self.robot_id = robot_marker_id

    def locate(self, frame, detections=None) -> Robot:
        """Find robot via ArUco-markør. 
        Returnerer RobotPosition med position OG heading."""
        if detections is None:
            detections = self.aruco.detect(frame)
        
        if self.robot_id not in detections:
            return None
        
        from config import ROBOT_MARKER_ROTATION_OFFSET
        
        corners = detections[self.robot_id]
        cx, cy = self.aruco.get_center(corners)
        heading = self.aruco.get_heading_deg(corners, rotation_offset=ROBOT_MARKER_ROTATION_OFFSET)
    
        return Robot(cx, cy, heading)
