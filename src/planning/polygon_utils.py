"""
GolfBot -- Polygon-hjælpefunktioner
====================================
Ray-casting point-in-polygon test og polygon-buffering via Shapely.

Bruges af pathfinder og route_planner til kollisionstest mod
forhindringers faktiske form (i stedet for en cirkulær radius).
"""

import math
from typing import List, Sequence, Tuple

from shapely.geometry import Polygon as ShapelyPolygon

Point = Tuple[float, float]


def point_in_polygon(x: float, y: float,
                     polygon: Sequence[Point]) -> bool:
    """Ray-casting point-in-polygon test.

    Returnerer True hvis (x, y) er INDEN I polygonen (eller paa kanten).
    Bruger ray-casting-algoritmen (O(n) for n polygon-punkter).
    Ingen eksterne afhaengigheder -- hurtig nok til pathfinding-hot-loops.
    """
    n = len(polygon)
    if n < 3:
        return False

    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        # Standard ray-casting: tael krydsninger med en vandret straale mod hoejre
        if ((yi > y) != (yj > y)) and \
           (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def buffer_polygon(polygon_cm: Sequence[Point],
                   margin_cm: float) -> List[Point]:
    """Udvid en polygon med 'margin_cm' i alle retninger.

    Bruger Shapely til korrekt haandtering af konkave polygoner
    (f.eks. et kryds der har indadgaaende hjoerner).

    Returnerer den udvidede polygons koordinater som en liste af (x, y)-tupler.
    Hvis polygonen er for lille eller ugyldig, returneres en tom liste.
    """
    if len(polygon_cm) < 3 or margin_cm < 0:
        return list(polygon_cm)

    try:
        poly = ShapelyPolygon(polygon_cm)
        if not poly.is_valid:
            poly = poly.buffer(0)  # fix self-intersections
        buffered = poly.buffer(margin_cm, join_style=2)  # 2 = mitre join
        if buffered.is_empty:
            return []
        # buffer() kan returnere MultiPolygon; tag den stoerste
        if buffered.geom_type == 'MultiPolygon':
            buffered = max(buffered.geoms, key=lambda g: g.area)
        coords = list(buffered.exterior.coords)
        # Shapely lukker polygonen (foerste == sidste); fjern duplikat
        if len(coords) > 1 and coords[0] == coords[-1]:
            coords = coords[:-1]
        return [(float(x), float(y)) for x, y in coords]
    except Exception:
        return list(polygon_cm)


def nearest_point_on_polygon(px: float, py: float,
                             polygon: Sequence[Point]) -> Point:
    """Find det naermeste punkt paa polygonens kant til (px, py).

    Bruges til at beregne approach-retningen naar en bold ligger taet paa
    forhindringens kant (i stedet for at bruge centroid-retningen).
    """
    best_dist = float('inf')
    best_point = (polygon[0][0], polygon[0][1]) if polygon else (px, py)
    n = len(polygon)
    for i in range(n):
        ax, ay = polygon[i]
        bx, by = polygon[(i + 1) % n]
        # Projicér (px, py) paa linjestykket (a, b)
        dx, dy = bx - ax, by - ay
        seg_len_sq = dx * dx + dy * dy
        if seg_len_sq == 0:
            t = 0.0
        else:
            t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len_sq))
        proj_x = ax + t * dx
        proj_y = ay + t * dy
        d = math.hypot(px - proj_x, py - proj_y)
        if d < best_dist:
            best_dist = d
            best_point = (proj_x, proj_y)
    return best_point
