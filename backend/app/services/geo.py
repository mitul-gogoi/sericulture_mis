"""GPS area calculation + future overlap helpers."""
from typing import List, Dict
import math

MIN_GPS_POINTS = 5  # business-rule minimum for a GPS submission (distinct from the ≥3 mathematical floor below)


def polygon_area_sqm(points: List[Dict[str, float]]) -> float:
    """Approx polygon area in sqm — equirectangular projection + shoelace."""
    if len(points) < 3:
        return 0.0
    R = 6378137.0
    mean_lat = sum(p["latitude"] for p in points) / len(points)
    coords = []
    for p in points:
        x = math.radians(p["longitude"]) * R * math.cos(math.radians(mean_lat))
        y = math.radians(p["latitude"]) * R
        coords.append((x, y))
    s = 0.0
    n = len(coords)
    for i in range(n):
        x1, y1 = coords[i]
        x2, y2 = coords[(i + 1) % n]
        s += (x1 * y2) - (x2 * y1)
    return abs(s) / 2.0


def points_to_wkt(points: List[Dict[str, float]]) -> str:
    """Convert [{latitude,longitude}] to WKT POLYGON string (lon lat order, closed ring)."""
    if len(points) < 3:
        raise ValueError("Need ≥ 3 points")
    coords = [(p["longitude"], p["latitude"]) for p in points]
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    coord_str = ", ".join(f"{lon} {lat}" for lon, lat in coords)
    return f"SRID=4326;POLYGON(({coord_str}))"
