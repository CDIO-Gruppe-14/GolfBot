"""
GolfBot -- Fase 1 + 7: Detektion
==================================
Finder alle bolde, robot og forhindringer via kamera.
Gemmer positioner i cm-koordinater.

Bruges baade som foerste fase (find alt) og som
fase 7 (tjek om der er flere bolde).
"""

import sys
import os
from typing import List, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.server.helpers.camera_utils import get_fresh_frame, extract_heading
from src.entities.ball import Ball
from src.entities.robot import Robot

def detect_robot(ctx):
    """
    Fase 1+7: Tag billede, find alle elementer, gem positioner.

    Udforer kalibrering og laver et overblik over hvor boldene
    ligger i koordinatsystemet.

    Args:
        ctx: GameContext med kamera og vision-moduler

    Returns:
        DetectionResult eller None hvis robot ikke kan findes.
    """
    frame = get_fresh_frame(ctx.camera)
    if frame is None:
        print("[Detektion] FEJL: Kunne ikke tage billede fra kamera")
        return None

    # Find robot
    robot = ctx.tracker.locate(frame)
    if robot is None:
        print("[Detektion] FEJL: Kunne ikke finde robot paa banen")
        return None

    ctx.robot.x, ctx.robot.y = ctx.field_map.pixel_to_cm(robot.x, robot.y)
    ctx.robot.heading = extract_heading(robot, ctx.field_map)
    
    print(f"[Detection] {ctx.robot}")

    return
    
def detect_balls(ctx):
    frame = get_fresh_frame(ctx.camera)
    if frame is None:
        print("[Detektion] FEJL: Kunne ikke tage billede fra kamera")
        return None
    
    # Find alle bolde
    all_balls = ctx.ball_detector.find_all_balls(frame)
    balls = []
    for b in all_balls:
        bx, by = ctx.field_map.pixel_to_cm(b.x, b.y)
        balls.append(Ball(b.color, bx, by, b.color))
        
    print("Fundne bolde:")
    for b in balls:
        print(f"[Detektion] {b}")

    return balls

def detect_obstacals(ctx):
    from config import FIELD_BORDER_MARGIN_PX, OBSTACLE_MIN_AREA_PX
    
    frame = get_fresh_frame(ctx.camera)
    if frame is None:
        return []

    color_detector = ctx.ball_detector.detector
    
    # 1. Find banens indre (ekskluderer den røde bande via margin)
    roi = color_detector.detect_field_roi(frame, margin=FIELD_BORDER_MARGIN_PX) 
    
    obstacles_cm = []
    
    # 2. Find det Røde Kryds inden for ROI
    if "roed" in color_detector.profiles:
        results = color_detector.detect_all(frame, "roed", roi=roi)
        for r in results:
            if r.found and r.center:
                # Vi kan ignorere meget små 'røde' prikker (støj)
                if r.area > OBSTACLE_MIN_AREA_PX: 
                    ox, oy = ctx.field_map.pixel_to_cm(r.center[0], r.center[1])
                    obstacles_cm.append((ox, oy))
                
    if obstacles_cm:
        print(f"[Detektion] Fundet {len(obstacles_cm)} forhindring(er) (Rødt Kryds):")
        for o in obstacles_cm:
            print(f"  - Forhindring på ({o[0]:.1f}, {o[1]:.1f}) cm")
            
    return obstacles_cm