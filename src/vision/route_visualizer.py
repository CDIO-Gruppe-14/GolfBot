"""
GolfBot -- Rute-visualisering
==============================
Viser den rute robotten VIL foelge (pathfinderens A*-sti) for en given scene,
saa man kan fejlsoege forhindrings-undvigelse uden at koere robotten.

To modes:

  python src/vision/route_visualizer.py --demo
      Syntetisk scene (ingen hardware). Tegner et top-down kort med bane,
      forhindringer + clearance-cirkler, robottens footprint og ruten.
      Gemmer docs/images/route_preview.png.

  python src/vision/route_visualizer.py --camera
      Tager et kamerabillede, detekterer bane/robot/bolde/forhindringer via
      ArUco + farve, planlaegger ruten og tegner den BAADE som top-down kort
      og som overlay paa selve kamerabilledet. Gemmer begge til docs/images/.

Forklaring paa tegningen:
  * Roedt kryds      = forhindring (det Roede Kryds)
  * Inderste cirkel  = krydsets MAALTE radius (fysisk udstraekning)
  * Lys roed cirkel  = krop-clearance (obstacle_radius + robot_radius)
  * Moerk roed cirkel = fuld clearance (obstacle_radius + safe_radius + robot_radius)
  * Bla ramme        = bande-inset: markoer-centret maa ikke udenfor
  * Groen polygon    = robottens footprint (FRONT/BACK/LEFT/RIGHT) i dens heading
  * Gul/hvid prikker = bolde (gul = orange VIP)
  * Farvede linjer   = ruten pr. bold i planlagt raekkefoelge
  * Hvid linje       = ruten fra sidste bold -> waypoint -> maal (Fase 5)
  * Hvid firkant     = waypoint foran maalet  |  Hvidt kryds = maalet
"""

import os
import sys
import argparse
from types import SimpleNamespace

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.entities.ball import Ball
from src.planning.pathfinder import find_path_adaptive
from src.server.phases.route_planner import plan_route, _normalize_obstacles
from config import (FIELD_SIZE_CM, OBSTACLE_SAFE_RADIUS_CM, ROBOT_RADIUS_CM,
                    ROBOT_FRONT_CM, ROBOT_BACK_CM, ROBOT_LEFT_CM, ROBOT_RIGHT_CM)

SCALE = 6  # pixels pr. cm i top-down kortet
LEG_COLORS = [(0, 220, 0), (0, 200, 200), (220, 120, 0),
              (200, 0, 200), (0, 120, 255), (200, 200, 0)]
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "docs", "images")


def _plan_one(start, target, obstacles_cm, field_w, field_h):
    """A*-leg fra start til target. Returnerer (pts, reachable, used_safe)."""
    route, used_safe = find_path_adaptive(
        start, target, obstacles_cm, field_w, field_h,
        safe_radius=OBSTACLE_SAFE_RADIUS_CM, robot_radius=ROBOT_RADIUS_CM)
    reachable = route is not None
    pts = [start] + (route if reachable else [target])
    return pts, reachable, used_safe


def _plan_goal_legs(start, obstacles_cm, field_w, field_h, goal=None):
    """Fase 5-ruten EFTER sidste bold: sidste position -> waypoint -> maal.

    Bruger samme waypoint/maal-kilde som serveren (goal_utils), saa plottet
    matcher den faktiske koersel. Begge ben planlaegges med A* udenom krydset
    (Trin 2 mod maalet undgaar nu ogsaa forhindringer)."""
    from src.server.helpers.goal_utils import compute_waypoint, load_goals
    if goal is None:
        goal, _ = load_goals()
    goal = (float(goal[0]), float(goal[1]))
    wp = compute_waypoint(goal[0], goal[1], field_w, field_h)

    leg_to_wp = _plan_one(start, wp, obstacles_cm, field_w, field_h)
    leg_to_goal = _plan_one(wp, goal, obstacles_cm, field_w, field_h)
    return [leg_to_wp, leg_to_goal], wp, goal


def plan_legs(robot_xy, balls, obstacles_cm, field_w, field_h, goal=None):
    """Planlaegger ruten pr. bold i samme raekkefoelge som spillet (orange sidst),
    EFTERFULGT af Fase 5-ruten til maalet via et waypoint.

    Returnerer (legs, order, goal_legs, waypoint, goal) hvor legs er bold-benene
    [(pts, reachable, used_safe)], order er boldene i planlagt raekkefoelge, og
    goal_legs er [sidste->waypoint, waypoint->maal]."""
    ctx = SimpleNamespace(
        robot=SimpleNamespace(x=robot_xy[0], y=robot_xy[1]),
        field_map=SimpleNamespace(field_size_cm=(field_w, field_h)),
    )
    order = list(plan_route(ctx, list(balls), obstacles_cm))

    legs = []
    start = (robot_xy[0], robot_xy[1])
    for ball in order:
        leg = _plan_one(start, (ball.x, ball.y), obstacles_cm, field_w, field_h)
        legs.append(leg)
        start = (ball.x, ball.y)

    goal_legs, waypoint, goal = _plan_goal_legs(
        start, obstacles_cm, field_w, field_h, goal)
    return legs, order, goal_legs, waypoint, goal


def _footprint_polygon(rx, ry, heading_deg):
    """Robottens fire hjoerner i cm ud fra FRONT/BACK/LEFT/RIGHT og heading."""
    h = np.radians(heading_deg)
    fx, fy = np.cos(h), np.sin(h)           # fremad
    lx, ly = -np.sin(h), np.cos(h)          # venstre (CCW 90 grader)
    corners = [
        (rx + fx * ROBOT_FRONT_CM + lx * ROBOT_LEFT_CM,
         ry + fy * ROBOT_FRONT_CM + ly * ROBOT_LEFT_CM),
        (rx + fx * ROBOT_FRONT_CM - lx * ROBOT_RIGHT_CM,
         ry + fy * ROBOT_FRONT_CM - ly * ROBOT_RIGHT_CM),
        (rx - fx * ROBOT_BACK_CM - lx * ROBOT_RIGHT_CM,
         ry - fy * ROBOT_BACK_CM - ly * ROBOT_RIGHT_CM),
        (rx - fx * ROBOT_BACK_CM + lx * ROBOT_LEFT_CM,
         ry - fy * ROBOT_BACK_CM + ly * ROBOT_LEFT_CM),
    ]
    return corners


def render_topdown(field_size, obstacles_cm, robot, balls, legs,
                   goal_legs=None, waypoint=None, goal=None):
    """Tegner et top-down kort af scenen + ruterne. Returnerer et BGR-billede."""
    fw, fh = field_size
    img = np.full((int(fh * SCALE), int(fw * SCALE), 3), 35, np.uint8)

    def P(x, y):
        return (int(round(x * SCALE)), int(round(y * SCALE)))

    # Bande + bande-inset (markoer-centret maa ikke udenfor inset'en)
    cv2.rectangle(img, P(0, 0), P(fw, fh), (90, 90, 90), 2)
    rr = ROBOT_RADIUS_CM
    cv2.rectangle(img, P(rr, rr), P(fw - rr, fh - rr), (110, 70, 50), 1)

    # Forhindringer med clearance-cirkler. Per-forhindring radius (obs[2]) laegges
    # oveni baade krop- og fuld clearance, saa cirklerne matcher pathfinderen.
    for obs in obstacles_cm:
        ox, oy = obs[0], obs[1]
        obs_r = obs[2] if len(obs) >= 3 else 0.0
        full = obs_r + OBSTACLE_SAFE_RADIUS_CM + ROBOT_RADIUS_CM
        body = obs_r + ROBOT_RADIUS_CM
        cv2.circle(img, P(ox, oy), int(full * SCALE), (60, 60, 130), 1)
        cv2.circle(img, P(ox, oy), int(body * SCALE), (80, 80, 220), 1)
        if obs_r > 0:
            cv2.circle(img, P(ox, oy), int(obs_r * SCALE), (40, 40, 90), 1)
        cv2.drawMarker(img, P(ox, oy), (0, 0, 255), cv2.MARKER_TILTED_CROSS, 16, 2)

    # Ruter pr. bold
    for i, (pts, reachable, _used) in enumerate(legs):
        color = LEG_COLORS[i % len(LEG_COLORS)] if reachable else (0, 0, 255)
        for a, b in zip(pts, pts[1:]):
            cv2.line(img, P(*a), P(*b), color, 2,
                     lineType=cv2.LINE_AA if reachable else cv2.LINE_4)
        for p in pts[1:]:
            cv2.circle(img, P(*p), 4, color, -1)

    # Mål-ruten (Fase 5): sidste bold -> waypoint -> maal, tegnet hvidt.
    for pts, reachable, _used in (goal_legs or []):
        color = (255, 255, 255) if reachable else (0, 0, 255)
        for a, b in zip(pts, pts[1:]):
            cv2.line(img, P(*a), P(*b), color, 2,
                     lineType=cv2.LINE_AA if reachable else cv2.LINE_4)
        for p in pts[1:]:
            cv2.circle(img, P(*p), 4, color, -1)
    if waypoint is not None:
        wp_px = P(*waypoint)
        cv2.rectangle(img, (wp_px[0] - 5, wp_px[1] - 5),
                      (wp_px[0] + 5, wp_px[1] + 5), (255, 255, 255), 2)
    if goal is not None:
        cv2.drawMarker(img, P(*goal), (255, 255, 255),
                       cv2.MARKER_TILTED_CROSS, 18, 2)

    # Bolde
    for ball in balls:
        c = (0, 165, 255) if ball.color == "orange" else (245, 245, 245)
        cv2.circle(img, P(ball.x, ball.y), int(3.5 * SCALE), c, -1)
        cv2.circle(img, P(ball.x, ball.y), int(3.5 * SCALE), (20, 20, 20), 1)

    # Robot footprint
    if robot is not None:
        poly = np.array([P(x, y) for x, y in
                         _footprint_polygon(robot.x, robot.y, robot.heading)],
                        np.int32)
        cv2.polylines(img, [poly], True, (0, 230, 0), 2)
        cv2.circle(img, P(robot.x, robot.y), 4, (0, 230, 0), -1)
        # heading-pil
        h = np.radians(robot.heading)
        cv2.arrowedLine(img, P(robot.x, robot.y),
                        P(robot.x + np.cos(h) * (ROBOT_FRONT_CM + 6),
                          robot.y + np.sin(h) * (ROBOT_FRONT_CM + 6)),
                        (0, 230, 0), 2, tipLength=0.3)

    return img


def _leg_tag(reachable, used_safe):
    if not reachable:
        return "SPRINGES OVER (indespaerret -- ingen sikker sti)"
    if used_safe is not None and used_safe < OBSTACLE_SAFE_RADIUS_CM:
        return "OK [reduceret buffer={:.0f} cm pga. traang bane]".format(used_safe)
    return "OK"


def _print_summary(legs, order, goal_legs=None):
    print("\n=== Planlagt rute ===")
    for i, (ball, (pts, reachable, used_safe)) in enumerate(zip(order, legs)):
        tag = _leg_tag(reachable, used_safe)
        wps = " -> ".join("({:.0f},{:.0f})".format(x, y) for x, y in pts)
        print(f"  Bold {i+1} [{ball.color}] @({ball.x:.0f},{ball.y:.0f}): {tag}")
        print(f"      {wps}")

    if goal_legs:
        labels = ["-> waypoint", "-> maal    "]
        print("  --- Fase 5: koer til maal ---")
        for label, (pts, reachable, used_safe) in zip(labels, goal_legs):
            wps = " -> ".join("({:.0f},{:.0f})".format(x, y) for x, y in pts)
            print(f"  {label}: {_leg_tag(reachable, used_safe)}")
            print(f"      {wps}")

    if any(not r for _, r, _ in legs):
        print("\n  Bemaerk: bolde markeret SPRINGES OVER er reelt indespaerret af"
              " forhindringer. Robotten koerer IKKE ind i krydset -- den springer"
              " dem over. Vil du naa dem, saa goer robot-footprint mindre.")


def run_demo():
    fw, fh = FIELD_SIZE_CM
    obstacles_cm = [(90, 60, 10.0)]                # Roedt Kryds (radius 10 cm) i midten
    robot = SimpleNamespace(x=20.0, y=60.0, heading=0.0)
    balls = [
        Ball(160, 60, "white"),                    # lige bag forhindringen
        Ball(90, 20, "white"),
        Ball(40, 95, "orange"),
    ]

    legs, order, goal_legs, waypoint, goal = plan_legs(
        (robot.x, robot.y), balls, obstacles_cm, fw, fh)
    _print_summary(legs, order, goal_legs)

    img = render_topdown((fw, fh), obstacles_cm, robot, balls, legs,
                         goal_legs=goal_legs, waypoint=waypoint, goal=goal)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out = os.path.join(OUTPUT_DIR, "route_preview.png")
    cv2.imwrite(out, img)
    print(f"\nTop-down kort gemt: {out}")
    _try_show("Rute (demo)", img)


def run_camera():
    from src.vision.camera import RobotCamera
    from src.vision.aruco_detector import ArucoDetector
    from src.vision.robot_tracker import RobotTracker
    from src.vision.color_detector import ColorDetector
    from src.vision.ball_detector import BallDetector
    from src.vision.obstacle_detector import ObstacleDetector
    from src.vision.field_map import FieldMap
    from config import ARUCO_DICT, ROBOT_MARKER_ID

    camera = RobotCamera()
    aruco = ArucoDetector(ARUCO_DICT)
    tracker = RobotTracker(aruco, ROBOT_MARKER_ID)
    detector = ColorDetector()
    detector.load_all_profiles()
    field_map = FieldMap(aruco_detector=aruco)
    ball_det = BallDetector(detector, field_map)
    obstacle_det = ObstacleDetector(detector, field_map)

    frame = camera.get_frame()
    if frame is None:
        print("FEJL: Kunne ikke tage billede fra kamera.")
        return
    if not field_map.calibrate_from_aruco(frame):
        print("ADVARSEL: ArUco bane-kalibrering fejlede -- bruger fallback-hjoerner.")

    fw, fh = field_map.field_size_cm

    robot_px = tracker.locate(frame)
    robot = None
    robot_xy = (fw / 2.0, fh / 2.0)
    if robot_px is not None:
        rx, ry = field_map.pixel_to_cm(robot_px.x, robot_px.y)
        robot = SimpleNamespace(x=rx, y=ry, heading=getattr(robot_px, "heading", 0.0))
        robot_xy = (rx, ry)
    else:
        print("ADVARSEL: Robot ikke fundet -- bruger banens midte som start.")

    balls = []
    for b in ball_det.find_all_balls(frame):
        bx, by = field_map.pixel_to_cm(b.x, b.y)
        balls.append(Ball(bx, by, b.color))

    from src.server.phases.detection import obstacle_radius_cm
    obstacles_cm = []
    for o in obstacle_det.find_obstacles(frame):
        ox, oy = field_map.pixel_to_cm(o.x, o.y)
        r = obstacle_radius_cm(field_map, o, ox, oy)
        obstacles_cm.append((ox, oy, r))

    print(f"Detekteret: {len(balls)} bolde, {len(obstacles_cm)} forhindring(er).")
    if not obstacles_cm:
        print("  Bemaerk: INGEN forhindringer detekteret -> ingen undvigelse"
              " planlaegges. Tjek farveprofil 'roed' / ObstacleDetector hvis der"
              " faktisk staar et kryds paa banen.")

    legs, order, goal_legs, waypoint, goal = plan_legs(
        robot_xy, balls, obstacles_cm, fw, fh)
    _print_summary(legs, order, goal_legs)

    # Top-down kort
    topdown = render_topdown((fw, fh), obstacles_cm, robot, balls, legs,
                             goal_legs=goal_legs, waypoint=waypoint, goal=goal)
    # Overlay paa selve kamerabilledet
    overlay = _draw_overlay(frame.copy(), field_map, obstacles_cm, balls, legs,
                            goal_legs=goal_legs, waypoint=waypoint, goal=goal)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    top_out = os.path.join(OUTPUT_DIR, "route_topdown.png")
    ov_out = os.path.join(OUTPUT_DIR, "route_overlay.png")
    cv2.imwrite(top_out, topdown)
    cv2.imwrite(ov_out, overlay)
    print(f"\nGemt:\n  {top_out}\n  {ov_out}")
    _try_show("Rute top-down", topdown)
    _try_show("Rute overlay", overlay)
    camera.release()


def _draw_overlay(frame, field_map, obstacles_cm, balls, legs,
                  goal_legs=None, waypoint=None, goal=None):
    """Tegner ruten + objekter oven paa kamerabilledet via cm_to_pixel."""
    def Q(x, y):
        px, py = field_map.cm_to_pixel(x, y)
        return (int(round(px)), int(round(py)))

    for obs in obstacles_cm:
        cv2.drawMarker(frame, Q(obs[0], obs[1]), (0, 0, 255),
                       cv2.MARKER_TILTED_CROSS, 22, 3)
    for i, (pts, reachable, _used) in enumerate(legs):
        color = LEG_COLORS[i % len(LEG_COLORS)] if reachable else (0, 0, 255)
        for a, b in zip(pts, pts[1:]):
            cv2.line(frame, Q(*a), Q(*b), color, 2, cv2.LINE_AA)
        for p in pts[1:]:
            cv2.circle(frame, Q(*p), 5, color, -1)

    # Mål-ruten (Fase 5), hvidt.
    for pts, reachable, _used in (goal_legs or []):
        color = (255, 255, 255) if reachable else (0, 0, 255)
        for a, b in zip(pts, pts[1:]):
            cv2.line(frame, Q(*a), Q(*b), color, 2, cv2.LINE_AA)
        for p in pts[1:]:
            cv2.circle(frame, Q(*p), 5, color, -1)
    if waypoint is not None:
        wp = Q(*waypoint)
        cv2.rectangle(frame, (wp[0] - 7, wp[1] - 7), (wp[0] + 7, wp[1] + 7),
                      (255, 255, 255), 2)
    if goal is not None:
        cv2.drawMarker(frame, Q(*goal), (255, 255, 255),
                       cv2.MARKER_TILTED_CROSS, 24, 2)

    for ball in balls:
        c = (0, 165, 255) if ball.color == "orange" else (245, 245, 245)
        cv2.circle(frame, Q(ball.x, ball.y), 8, c, 2)
    return frame


def _try_show(title, img):
    """Viser et vindue hvis der er et display; ellers stille videre."""
    try:
        cv2.imshow(title, img)
        print("Tryk en tast i vinduet for at lukke...")
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except cv2.error:
        pass


def main():
    parser = argparse.ArgumentParser(description="GolfBot rute-visualisering")
    parser.add_argument("--camera", action="store_true",
                        help="Brug live kamera + detektion (ellers syntetisk demo)")
    parser.add_argument("--demo", action="store_true",
                        help="Syntetisk scene uden hardware (default)")
    args = parser.parse_args()
    if args.camera:
        run_camera()
    else:
        run_demo()


if __name__ == "__main__":
    main()
