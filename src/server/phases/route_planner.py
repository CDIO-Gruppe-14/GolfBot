"""
GolfBot -- Fase 2: Ruteplanlaegning
======================================
Beregner optimal raekkefoelge for bolde via prioritetskoee.

Nuvaerende implementering: simpel afstandssortering.
Forberedt til A*-pathfinding via src/planning/pathfinder.py.
"""

import heapq
import math
from collections import deque
from typing import Deque, Dict, Iterable, List, Sequence, Set, Tuple

from src.entities.ball import Ball
from src.entities.obstacals import Obstacle
from src.planning.polygon_utils import point_in_polygon, buffer_polygon
from shapely.geometry import Polygon as ShapelyPolygon, Point as ShapelyPoint


def _normalize_obstacles(obstacles: Iterable) -> List[Obstacle]:
    """Normaliser forhindringer til en liste af Obstacle-objekter.

    Haandterer baade nye Obstacle-objekter og legacy (x, y)-tupler
    (til bagudkompatibilitet under overgangsperioden).
    """
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
        elif hasattr(obstacle, "x") and hasattr(obstacle, "y"):
            from config import OBSTACLE_SAFE_RADIUS_CM, ROBOT_RADIUS_CM
            ox, oy = float(obstacle.x), float(obstacle.y)
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

# --- TRIN 1: A* STIFINDING ---
def a_star_distance(start: Ball, goal: Ball, obstacles: List[Obstacle], max_x: int, max_y: int) -> float:
    """A*-afstandsberegning med polygon-baseret kollision."""
    if start.x == goal.x and start.y == goal.y:
        return 0.0

    open_set = []
    heapq.heappush(open_set, (0, (int(start.x), int(start.y))))
    
    g_score = {(int(start.x), int(start.y)): 0.0}
    
    from config import OBSTACLE_SAFE_RADIUS_CM, ROBOT_RADIUS_CM
    
    # Heuristik: Euklidisk afstand i fugleflugt
    def h(pos):
        return math.hypot(pos[0] - goal.x, pos[1] - goal.y)

    # Byg effektive kollisions-polygoner med tolerance for start/maal
    eff_buffer = OBSTACLE_SAFE_RADIUS_CM + ROBOT_RADIUS_CM
    collision_polygons = []
    for obs in obstacles:
        start_blocked = point_in_polygon(start.x, start.y, obs.buffered_polygon_cm)
        goal_blocked = point_in_polygon(goal.x, goal.y, obs.buffered_polygon_cm)
        if not start_blocked and not goal_blocked:
            collision_polygons.append(obs.buffered_polygon_cm)
        else:
            try:
                raw_poly = ShapelyPolygon(obs.polygon_cm)
                if not raw_poly.is_valid:
                    raw_poly = raw_poly.buffer(0)
                dist_start = raw_poly.exterior.distance(ShapelyPoint(start.x, start.y))
                dist_goal = raw_poly.exterior.distance(ShapelyPoint(goal.x, goal.y))
                allowed = max(0.0, min(eff_buffer, dist_start - 1.0, dist_goal - 1.0))
                if allowed > 0.5:
                    collision_polygons.append(buffer_polygon(obs.polygon_cm, allowed))
                else:
                    collision_polygons.append([])
            except Exception:
                collision_polygons.append([])

    while open_set:
        _, current = heapq.heappop(open_set)

        if current[0] == int(goal.x) and current[1] == int(goal.y):
            return g_score[current]

        # Tjek de 8 mulige retninger (inkl. diagonalt)
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1), (-1,-1), (-1,1), (1,-1), (1,1)]:
            neighbor = (current[0] + dx, current[1] + dy)

            # Tjek om vi er inden for banens grænser
            if 0 <= neighbor[0] <= max_x and 0 <= neighbor[1] <= max_y:
                
                # Polygon-baseret kollisionstest
                is_blocked = False
                for poly in collision_polygons:
                    if poly and point_in_polygon(neighbor[0], neighbor[1], poly):
                        is_blocked = True
                        break
                
                if not is_blocked:
                    # Diagonal bevægelse koster ~1.414, lige bevægelse koster 1
                    cost = math.hypot(dx, dy)
                    tentative_g_score = g_score[current] + cost

                    if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                        g_score[neighbor] = tentative_g_score
                        f_score = tentative_g_score + h(neighbor)
                        heapq.heappush(open_set, (f_score, neighbor))

    return float('inf') # Returnerer uendelig, hvis ruten er fuldstændig blokeret

# --- TRIN 2: BYG AFSTANDSMATRIX ---
def build_distance_matrix(nodes: Sequence[Ball], obstacles: List[Tuple[float, float]], max_x: int, max_y: int) -> Dict:
    matrix = {}
    for i in range(len(nodes)):
        matrix[(i, i)] = 0.0
        for j in range(i + 1, len(nodes)):
            dist = a_star_distance(nodes[i], nodes[j], obstacles, max_x, max_y)
            matrix[(i, j)] = dist
            matrix[(j, i)] = dist
    return matrix

# --- TRIN 3: 2-OPT RUTEOPTIMERING ---
def optimize_robot_route(robot_start: Ball, balls: List[Ball], obstacles: Set[Tuple[int, int]], grid_max_x: int, grid_max_y: int) -> Deque[Ball]:
    # Saml alle punkter for at bygge matricen
    all_nodes = [robot_start] + balls

    if len(all_nodes) <= 1:
        return deque()
    
    print("Beregner A* afstandsmatrix...")
    matrix = build_distance_matrix(all_nodes, obstacles, grid_max_x, grid_max_y)

    # Initial rute (rækkefølgen startpositionen efterfulgt af boldene som de står i listen)
    route = list(range(len(all_nodes)))
    
    def calc_total_distance(r):
        return sum(matrix[(r[i], r[i + 1])] for i in range(len(r) - 1))

    print("Kører 2-Opt optimering...")
    improvement = True
    while improvement:
        improvement = False
        best_dist = calc_total_distance(route)

        # Vi starter fra index 1, da robotten altid skal starte i 'robot_start'
        for i in range(1, len(route) - 1):
            for k in range(i + 1, len(route)):
                # Vend sub-ruten mellem i og k
                new_route = route[:i] + route[i:k + 1][::-1] + route[k + 1:]
                new_dist = calc_total_distance(new_route)

                if new_dist < best_dist:
                    route = new_route
                    best_dist = new_dist
                    improvement = True
                    break # Afbryd indre loop og start forfra med den forbedrede rute
            if improvement:
                break

    # Konverter den optimerede liste af navne tilbage til en prioritetskø af faktiske Ball-objekter
    optimal_queue = deque()
    
    # Vi ignorerer route[0] (robottens startposition), da den kun skal hente boldene
    for index in route[1:]:
        optimal_queue.append(all_nodes[index])

    return optimal_queue


def plan_route(ctx, balls, obstacals):
    """
    Fase 2: Returnerer en standard deque med bolde i prioriteret rækkefølge.
    """
    if not balls:
        print("[Ruteplaner] Ingen bolde at planlaegge rute for")
        return deque()

    field_width, field_height = getattr(ctx.field_map, "field_size_cm", (180, 120))
    robot_start = Ball(
        float(getattr(ctx.robot, "x", 0.0)),
        float(getattr(ctx.robot, "y", 0.0)),
        "robot",
        "robot",
    )

    obstacles = _normalize_obstacles(obstacals)

    # Orange er VIP-bolden: 200 bonuspoint HVIS den afleveres foerst.
    # Robotten holder bolde efter LIFO -> orange skal samles SIDST, saa den
    # ligger oeverst i magasinet og afleveres foerst. Derfor optimeres KUN de
    # hvide boldes raekkefoelge; orange append'es til sidst.
    orange_balls = [b for b in balls if b.color == "orange"]
    white_balls = [b for b in balls if b.color != "orange"]

    sorted_balls = optimize_robot_route(
        robot_start,
        white_balls,
        obstacles,
        int(field_width),
        int(field_height),
    )
    for orange in orange_balls:
        sorted_balls.append(orange)

    print("[Ruteplaner] Planlagt raekkefoelge for {} bolde:".format(len(sorted_balls)))
    for i, ball in enumerate(sorted_balls):
        dist = math.hypot(ball.x - robot_start.x, ball.y - robot_start.y)
        print("  {}: ({:.1f}, {:.1f}) {} - {:.1f} cm vaek".format(
            i + 1, ball.x, ball.y, ball.color, dist))

    return sorted_balls
