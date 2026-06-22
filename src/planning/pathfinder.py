"""
GolfBot -- Pathfinder (A* med sti-output)
==========================================
Grid-baseret A* der returnerer SELVE STIEN (en liste af cm-waypoints) udenom
forhindringer -- i modsaetning til route_planner.a_star_distance, der kun
returnerer afstanden til ruteplanlaegning.

Bruges af drive_to_ball (Fase 3) til at koere udenom det Roede Kryds i stedet
for tvaers igennem. Banderne ligger paa kendte cm-koordinater (ArUco-banen
mapper hjoernerne til 0..max_x / 0..max_y), saa A* holder sig automatisk inden
for grid-graenserne.

Design:
  - find_path() laver foerst en billig line-of-sight test: er der fri sigtelinje
    fra start til maal, returneres blot [maal] uden A* (det normale tilfaelde).
  - Ellers koeres grid-A* (8-forbundet) og stien forenkles med "string-pulling"
    (line-of-sight) til faa knaekpunkter, saa robotten ikke koerer i 1 cm-trin.
  - Start/maal kan ligge taet paa en forhindring (bold ved kryds): pr.-forhindring
    tolerance tillader at komme saa taet paa som start/maal allerede er -- samme
    logik som route_planner.a_star_distance.
"""

import math
import heapq
from typing import List, Optional, Sequence, Tuple

from src.entities.obstacals import Obstacle
from src.planning.polygon_utils import point_in_polygon, buffer_polygon
from shapely.geometry import Polygon as ShapelyPolygon, Point as ShapelyPoint

Point = Tuple[float, float]


def _normalize_obstacles(obstacles: Sequence) -> List[Obstacle]:
    normalized = []
    for obstacle in obstacles or []:
        if isinstance(obstacle, Obstacle):
            normalized.append(obstacle)
        elif isinstance(obstacle, (tuple, list)) and len(obstacle) >= 2:
            from config import OBSTACLE_SAFE_RADIUS_CM, ROBOT_RADIUS_CM
            ox, oy = float(obstacle[0]), float(obstacle[1])
            margin = OBSTACLE_SAFE_RADIUS_CM + ROBOT_RADIUS_CM
            n_pts = 12
            polygon = [
                (ox + 0.1 * math.cos(2 * math.pi * i / n_pts),
                 oy + 0.1 * math.sin(2 * math.pi * i / n_pts))
                for i in range(n_pts)
            ]
            buffered = [
                (ox + margin * math.cos(2 * math.pi * i / n_pts),
                 oy + margin * math.sin(2 * math.pi * i / n_pts))
                for i in range(n_pts)
            ]
            normalized.append(Obstacle(
                center_x=ox, center_y=oy,
                polygon_cm=polygon, buffered_polygon_cm=buffered,
            ))
    return normalized


def _build_collision_polygons(start: Point, goal: Point,
                              obstacles: Sequence,
                              safe_radius: float,
                              robot_radius: float) -> List[List[Point]]:
    """For hver forhindring: byg den effektive kollisions-polygon.

    Normalt bruges den fulde buffered_polygon_cm. Men hvis start eller maal
    ligger INDEN I den bufferede polygon (bold taet paa krydset), reduceres
    bufferen for den specifikke forhindring saa stien stadig er mulig --
    samme semantik som den gamle radius-tolerance."""
    obstacles = _normalize_obstacles(obstacles)
    eff_buffer = safe_radius + robot_radius
    result = []
    for obs in obstacles:
        start_blocked = point_in_polygon(start[0], start[1], obs.buffered_polygon_cm)
        goal_blocked = point_in_polygon(goal[0], goal[1], obs.buffered_polygon_cm)
        if not start_blocked and not goal_blocked:
            result.append(obs.buffered_polygon_cm)
        else:
            try:
                raw_poly = ShapelyPolygon(obs.polygon_cm)
                if not raw_poly.is_valid:
                    raw_poly = raw_poly.buffer(0)
                dist_start = raw_poly.exterior.distance(ShapelyPoint(start))
                dist_goal = raw_poly.exterior.distance(ShapelyPoint(goal))
                allowed = max(0.0, min(eff_buffer, dist_start - 1.0, dist_goal - 1.0))
                if allowed > 0.5:
                    result.append(buffer_polygon(obs.polygon_cm, allowed))
                else:
                    result.append([])
            except Exception:
                result.append([])
    return result


def _blocked(x: float, y: float,
             collision_polygons: Sequence[Sequence[Point]]) -> bool:
    """Polygon-baseret kollisionstest: er (x, y) inden i nogen forhindring?"""
    for poly in collision_polygons:
        if poly and point_in_polygon(x, y, poly):
            return True
    return False


def _line_clear(p0: Point, p1: Point,
                collision_polygons: Sequence[Sequence[Point]],
                step: float = 1.0) -> bool:
    """Fri sigtelinje mellem to punkter (samplet pr. 'step' cm)."""
    dist = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    if dist == 0:
        return not _blocked(p0[0], p0[1], collision_polygons)
    n = max(1, int(dist / step))
    for i in range(n + 1):
        t = i / n
        x = p0[0] + (p1[0] - p0[0]) * t
        y = p0[1] + (p1[1] - p0[1]) * t
        if _blocked(x, y, collision_polygons):
            return False
    return True


def _simplify(points: List[Point],
              collision_polygons: Sequence[Sequence[Point]]) -> List[Point]:
    """String-pulling: behold kun de knaekpunkter der er noedvendige, ved at
    springe saa langt frem som der er fri sigtelinje."""
    if len(points) <= 2:
        return points
    result = [points[0]]
    i = 0
    while i < len(points) - 1:
        j = len(points) - 1
        while j > i + 1 and not _line_clear(points[i], points[j], collision_polygons):
            j -= 1
        result.append(points[j])
        i = j
    return result


def find_path(start: Point, goal: Point,
              obstacles: Sequence[Obstacle],
              max_x: float, max_y: float,
              safe_radius: float,
              robot_radius: float = 0.0) -> Optional[List[Point]]:
    """Returnerer en forenklet liste af cm-waypoints fra start (eksklusiv) til
    maal (inklusiv) udenom forhindringerne.

    Kollisionsmodellen er polygon-baseret: forhindringens faktiske form bruges
    i stedet for en cirkulaer radius.

    - Fri sigtelinje: returnerer [maal].
    - Ingen sti mulig: returnerer None.
    """
    # Byg effektive kollisions-polygoner (med tolerance for start/maal)
    collision_polygons = _build_collision_polygons(
        start, goal, obstacles, safe_radius, robot_radius)

    # Billig genvej: ingen forhindring i vejen -> kør direkte.
    if _line_clear(start, goal, collision_polygons):
        return [(float(goal[0]), float(goal[1]))]

    # Banderne: markoer-centret skal holde 'robot_radius' fra hver vaeg, ellers
    # rammer kroppen banden. Indskraenker det koerbare omraade tilsvarende.
    lo_x, hi_x = robot_radius, max_x - robot_radius
    lo_y, hi_y = robot_radius, max_y - robot_radius

    def _clamp(v, lo, hi):
        return max(lo, min(hi, v))

    sx = int(round(_clamp(start[0], lo_x, hi_x)))
    sy = int(round(_clamp(start[1], lo_y, hi_y)))
    gx = int(round(_clamp(goal[0], lo_x, hi_x)))
    gy = int(round(_clamp(goal[1], lo_y, hi_y)))
    mnx, mxx = int(math.ceil(lo_x)), int(hi_x)
    mny, mxy = int(math.ceil(lo_y)), int(hi_y)

    def h(pos):
        return math.hypot(pos[0] - gx, pos[1] - gy)

    open_set = [(h((sx, sy)), (sx, sy))]
    g_score = {(sx, sy): 0.0}
    came_from = {}

    neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1),
                 (-1, -1), (-1, 1), (1, -1), (1, 1)]

    goal_node = (gx, gy)
    found = False
    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal_node:
            found = True
            break
        cx, cy = current
        for dx, dy in neighbors:
            nb = (cx + dx, cy + dy)
            if not (mnx <= nb[0] <= mxx and mny <= nb[1] <= mxy):
                continue
            if _blocked(nb[0], nb[1], collision_polygons):
                continue
            tentative = g_score[current] + math.hypot(dx, dy)
            if nb not in g_score or tentative < g_score[nb]:
                g_score[nb] = tentative
                came_from[nb] = current
                heapq.heappush(open_set, (tentative + h(nb), nb))

    if not found:
        return None

    # Rekonstruer sti fra maal tilbage til start.
    path = [goal_node]
    node = goal_node
    while node in came_from:
        node = came_from[node]
        path.append(node)
    path.reverse()
    path = [(float(x), float(y)) for x, y in path]

    # Forenkl og drop selve startpunktet; sikr at det praecise maal er sidste punkt.
    simplified = _simplify(path, collision_polygons)
    waypoints = simplified[1:] if len(simplified) > 1 else simplified
    if waypoints:
        waypoints[-1] = (float(goal[0]), float(goal[1]))
    else:
        waypoints = [(float(goal[0]), float(goal[1]))]
    return waypoints


def find_path_adaptive(start: Point, goal: Point,
                       obstacles: Sequence[Obstacle],
                       max_x: float, max_y: float,
                       safe_radius: float,
                       robot_radius: float = 0.0):
    """find_path med automatisk nedtrapning af den strategiske buffer hvis banen
    er for traang til den fulde clearance.

    robot_radius beholdes ALTID (robotkroppen undgaar fysisk forhindringen);
    kun safe_radius trappes ned (1.0 -> 0.5 -> 0.0 af den). Det forhindrer at en
    stor robot paa en lille bane goer alle bolde "uopnaaelige" -- mens kroppen
    stadig holdes fri.

    Returnerer (path, used_safe_radius). Hvis selv 0-buffer ikke giver en sti
    (bolden er reelt indespaerret), returneres (None, None) -- saa kalderen kan
    springe bolden over i stedet for at koere ind i forhindringen.
    """
    obstacles = _normalize_obstacles(obstacles)
    for factor in (1.0, 0.5, 0.0):
        safe = safe_radius * factor
        # Ved reduceret buffer genberegnes forhindringernes buffered polygon
        if factor < 1.0:
            reduced = []
            margin = safe + robot_radius
            for obs in obstacles:
                if obs.polygon_cm and len(obs.polygon_cm) >= 3:
                    new_buf = buffer_polygon(obs.polygon_cm, margin)
                else:
                    new_buf = obs.buffered_polygon_cm
                reduced.append(Obstacle(
                    center_x=obs.center_x, center_y=obs.center_y,
                    polygon_cm=obs.polygon_cm, buffered_polygon_cm=new_buf))
            path = find_path(start, goal, reduced, max_x, max_y, safe, robot_radius)
        else:
            path = find_path(start, goal, obstacles, max_x, max_y, safe, robot_radius)
        if path is not None:
            return path, safe
    return None, None
