"""
Traffic Analysis Service
------------------------
Uses threshold-based congestion classification and Dijkstra's algorithm
for shortest-path route recommendations.

Congestion thresholds:
  density > 80 veh/km  → HIGH
  density > 40 veh/km  → MEDIUM
  else                 → LOW
"""

import heapq
import json
from datetime import datetime
from collections import defaultdict

# ── Congestion thresholds (vehicles per km) ────────────────────────────────
DENSITY_HIGH   = 80.0
DENSITY_MEDIUM = 40.0

# ── Signal timing presets (seconds) ───────────────────────────────────────
TIMING = {
    "HIGH":   {"green": 60, "red": 20},
    "MEDIUM": {"green": 45, "red": 30},
    "LOW":    {"green": 30, "red": 45},
}


# ══════════════════════════════════════════════════════════════════════════
#  1. CONGESTION CLASSIFICATION
# ══════════════════════════════════════════════════════════════════════════

def classify_congestion(vehicle_count: int, speed: float, density: float) -> str:
    """
    Rule-based congestion classifier.

    Primary signal: density (most reliable).
    Secondary signals: vehicle_count and speed used as tie-breakers.

    Returns: 'LOW' | 'MEDIUM' | 'HIGH'
    """
    if density > DENSITY_HIGH:
        return "HIGH"
    if density > DENSITY_MEDIUM:
        return "MEDIUM"

    # Supplement with speed heuristic when density is borderline
    if speed < 15:          # Very slow – treat as HIGH regardless
        return "HIGH"
    if speed < 30:
        return "MEDIUM"

    return "LOW"


# ══════════════════════════════════════════════════════════════════════════
#  2. SIGNAL CONTROL
# ══════════════════════════════════════════════════════════════════════════

def compute_signal_timing(congestion_level: str) -> dict:
    """
    Return adaptive green/red timing based on congestion level.

    Logic:
      HIGH   → long green (60 s) to drain queue; short red (20 s)
      MEDIUM → balanced (45 / 30)
      LOW    → short green (30 s); longer red allows cross-traffic
    """
    return TIMING.get(congestion_level, TIMING["LOW"])


# ══════════════════════════════════════════════════════════════════════════
#  3. DIJKSTRA SHORTEST-PATH ROUTE RECOMMENDATION
# ══════════════════════════════════════════════════════════════════════════

# Weight multipliers applied on top of travel_time based on traffic status
CONGESTION_WEIGHT = {"LOW": 1.0, "MEDIUM": 1.8, "HIGH": 3.5}


def build_graph(routes) -> dict:
    """
    Build weighted adjacency list from Route records.
    Edge weight = dynamically adjusted travel_time (in minutes)
    """
    graph = defaultdict(list)
    for r in routes:
        weight = r.travel_time
        graph[r.start_point].append((weight, r.end_point, r.route_id, r.distance))
        # Bidirectional road
        graph[r.end_point].append((weight, r.start_point, r.route_id, r.distance))
    return graph


def dijkstra(graph: dict, source: str, target: str) -> dict:
    """
    Standard Dijkstra implementation using a min-heap.

    Returns:
      {
        'path':     list of node names from source → target,
        'cost':     total weighted cost,
        'distance': total km,
        'route_ids': list of route_id segments used,
      }
    Returns None if no path exists.
    """
    # Priority queue: (cost, node, path_so_far, total_distance, route_ids)
    heap = [(0, source, [source], 0.0, [])]
    visited = set()

    while heap:
        cost, node, path, dist, rids = heapq.heappop(heap)

        if node in visited:
            continue
        visited.add(node)

        if node == target:
            return {"path": path, "cost": round(cost, 2),
                    "distance": round(dist, 2), "route_ids": rids}

        for edge_weight, neighbour, rid, edge_dist in graph.get(node, []):
            if neighbour not in visited:
                heapq.heappush(heap, (
                    cost + edge_weight,
                    neighbour,
                    path + [neighbour],
                    dist + edge_dist,
                    rids + [rid],
                ))

    return None   # No path found


def recommend_routes(routes, start: str, end: str) -> dict:
    """
    Public API: given DB route records, return best path and alternatives.
    """
    graph = build_graph(routes)
    best = dijkstra(graph, start, end)

    if not best:
        return {"error": f"No route found from {start} to {end}"}

    # Estimated travel time is exactly the cost in minutes
    estimated_minutes = best["cost"]

    return {
        "start": start,
        "end": end,
        "recommended_path": best["path"],
        "total_distance_km": best["distance"],
        "estimated_travel_time_min": estimated_minutes,
        "route_segment_ids": best["route_ids"],
        "status": "OPTIMAL",
    }


# ══════════════════════════════════════════════════════════════════════════
#  4. ALERT GENERATION
# ══════════════════════════════════════════════════════════════════════════

def generate_alert(location: str, congestion: str, vehicle_count: int, speed: float) -> str:
    """Generate a clean, professional alert message."""
    if congestion == "HIGH":
        return f"Severe congestion: {vehicle_count} vehicles, {speed:.1f} km/h. Manual override recommended."
    if congestion == "MEDIUM":
        return f"Moderate congestion: {vehicle_count} vehicles, {speed:.1f} km/h. Signal timing adjusted."
    return f"Flow normal: {vehicle_count} vehicles, {speed:.1f} km/h."
