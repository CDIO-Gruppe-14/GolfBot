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

Point = Tuple[float, float]


def _build_tolerances(start: Point, goal: Point,
                      obstacles: Sequence[Point],
                      safe_radius: float) -> List[Tuple[float, float, float]]:
    """For hver forhindring: hvor taet maa en celle komme.

    Normalt safe_radius, men aldrig taettere end at start/maal selv kan rummes
    (saa en bold lige ved krydset ikke goer ruten umulig)."""
    tolerances = []
    for ox, oy in obstacles:
        dist_goal = math.hypot(goal[0] - ox, goal[1] - oy)
        dist_start = math.hypot(start[0] - ox, start[1] - oy)
        allowed = max(0.0, min(safe_radius, dist_goal - 1.0, dist_start - 1.0))
        tolerances.append((ox, oy, allowed))
    return tolerances


def _blocked(x: float, y: float,
             tolerances: Sequence[Tuple[float, float, float]]) -> bool:
    for ox, oy, allowed in tolerances:
        if math.hypot(x - ox, y - oy) < allowed:
            return True
    return False


def _line_clear(p0: Point, p1: Point,
                tolerances: Sequence[Tuple[float, float, float]],
                step: float = 1.0) -> bool:
    """Fri sigtelinje mellem to punkter (samplet pr. 'step' cm)."""
    dist = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
    if dist == 0:
        return not _blocked(p0[0], p0[1], tolerances)
    n = max(1, int(dist / step))
    for i in range(n + 1):
        t = i / n
        x = p0[0] + (p1[0] - p0[0]) * t
        y = p0[1] + (p1[1] - p0[1]) * t
        if _blocked(x, y, tolerances):
            return False
    return True


def _simplify(points: List[Point],
              tolerances: Sequence[Tuple[float, float, float]]) -> List[Point]:
    """String-pulling: behold kun de knaekpunkter der er noedvendige, ved at
    springe saa langt frem som der er fri sigtelinje."""
    if len(points) <= 2:
        return points
    result = [points[0]]
    i = 0
    while i < len(points) - 1:
        j = len(points) - 1
        while j > i + 1 and not _line_clear(points[i], points[j], tolerances):
            j -= 1
        result.append(points[j])
        i = j
    return result


def find_path(start: Point, goal: Point,
              obstacles: Sequence[Point],
              max_x: float, max_y: float,
              safe_radius: float,
              robot_radius: float = 0.0) -> Optional[List[Point]]:
    """Returnerer en forenklet liste af cm-waypoints fra start (eksklusiv) til
    maal (inklusiv) udenom forhindringerne.

    robot_radius: robottens udstraekning fra det trackede markoer-center (cm).
      Robotten er stoerre end ArUco-markoeren, saa dens KROP -- ikke kun centret --
      skal gaa fri. Radiussen laegges til forhindrings-clearancen, og det koerbare
      omraade indskraenkes 'robot_radius' fra hver bande (markoer-centret maa ikke
      komme taettere paa en vaeg). Default 0 = planlaeg for et punkt (markoer-centret).

    - Fri sigtelinje: returnerer [maal].
    - Ingen sti mulig: returnerer None.
    """
    # Krop-clearance: forhindringerne holdes paa safe_radius + robottens radius
    # fra markoer-centret, saa selve robotkroppen aldrig roerer dem.
    eff_radius = safe_radius + robot_radius
    tolerances = _build_tolerances(start, goal, obstacles, eff_radius)

    # Billig genvej: ingen forhindring i vejen -> kør direkte.
    if _line_clear(start, goal, tolerances):
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
            if _blocked(nb[0], nb[1], tolerances):
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
    simplified = _simplify(path, tolerances)
    waypoints = simplified[1:] if len(simplified) > 1 else simplified
    if waypoints:
        waypoints[-1] = (float(goal[0]), float(goal[1]))
    else:
        waypoints = [(float(goal[0]), float(goal[1]))]
    return waypoints


def find_path_adaptive(start: Point, goal: Point,
                       obstacles: Sequence[Point],
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
    for factor in (1.0, 0.5, 0.0):
        safe = safe_radius * factor
        path = find_path(start, goal, obstacles, max_x, max_y, safe, robot_radius)
        if path is not None:
            return path, safe
    return None, None
