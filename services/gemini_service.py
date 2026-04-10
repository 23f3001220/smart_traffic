"""
Gemini AI Service – RAG-Powered Traffic Intelligence
-----------------------------------------------------
Uses Google Gemini to:
  1. Generate AI insights from traffic data (RAG pattern)
  2. Answer authority queries using retrieved context
  3. Produce natural-language reports
  4. Generate a simulated traffic dataset
"""

import os
import json
import random
import textwrap
from datetime import datetime, timedelta

try:
    from google import genai as _genai_sdk
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# ── Configure Gemini ───────────────────────────────────────────────────────
GEMINI_MODEL = "gemini-2.5-flash"

_client = None


def _get_client():
    """Lazy-init Gemini client – reads GEMINI_API_KEY from env on each call."""
    global _client
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if _client is None and GEMINI_AVAILABLE and api_key:
        _client = _genai_sdk.Client(api_key=api_key)
    return _client


# ══════════════════════════════════════════════════════════════════════════
#  RAG CONTEXT BUILDER
# ══════════════════════════════════════════════════════════════════════════

def build_rag_context(traffic_records: list, signals: list, reports: list) -> str:
    """
    Retrieves and formats the most relevant traffic data as a
    structured context block – the 'Retrieval' step of RAG.
    """
    lines = ["=== RETRIEVED TRAFFIC CONTEXT ===\n"]

    # Top 5 most congested locations
    congested = sorted(
        traffic_records,
        key=lambda r: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(r.get("congestion_level", "LOW"), 1),
        reverse=True
    )[:5]

    lines.append("-- Top Congestion Points --")
    for r in congested:
        lines.append(
            f"  • {r['location']}: {r['congestion_level']} | "
            f"{r['vehicle_count']} vehicles | speed {r['speed']} km/h | "
            f"density {r['density']} veh/km"
        )

    # Signal states
    lines.append("\n-- Current Signal States --")
    for s in signals[:6]:
        lines.append(
            f"  • {s['location']}: {s['status']} | green={s['green_time']}s | mode={s['mode']}"
        )

    # Recent alerts
    high_alerts = [r for r in reports if r.get("congestion_level") == "HIGH"][:3]
    if high_alerts:
        lines.append("\n-- Active HIGH Congestion Alerts --")
        for a in high_alerts:
            lines.append(f"  • {a['location']}: {a['alert_message'][:120]}")

    lines.append("\n=== END CONTEXT ===")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════
#  GEMINI INFERENCE CALLS
# ══════════════════════════════════════════════════════════════════════════

def _call_gemini(prompt: str, fallback: str) -> str:
    """Call Gemini API with fallback for missing key."""
    client = _get_client()
    if not client:
        return fallback
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"{fallback} [Gemini error: {str(e)[:80]}]"


def analyze_traffic_with_ai(traffic_records: list, signals: list, reports: list) -> str:
    """
    RAG pipeline: retrieve context → augment prompt → generate insight.
    """
    context = build_rag_context(traffic_records, signals, reports)

    prompt = textwrap.dedent(f"""
        You are an expert urban traffic management AI assistant.
        Below is real-time retrieved traffic data from sensors across the city.

        {context}

        Based on this data, provide:
        1. A concise executive summary (2-3 sentences) of current city-wide traffic status.
        2. Top 2 action recommendations for traffic control authorities.
        3. Predicted traffic trend for the next 30 minutes.

        Keep the response professional, concise, and actionable.
        Format in clear numbered sections.
    """)

    fallback = (
        "⚠️  AI analysis unavailable (no Gemini API key configured). "
        "Traffic data collected successfully. Please set GEMINI_API_KEY environment variable "
        "to enable AI-powered insights."
    )
    return _call_gemini(prompt, fallback)


def get_ai_route_advice(start: str, end: str, route_data: dict, traffic_snapshot: list) -> str:
    """
    Generate natural-language route advice augmented with live traffic context.
    """
    path_str = " → ".join(route_data.get("recommended_path", [start, end]))
    dist = route_data.get("total_distance_km", "N/A")
    eta = route_data.get("estimated_travel_time_min", "N/A")

    # Build mini context for RAG
    relevant = [r for r in traffic_snapshot
                if r.get("location") in route_data.get("recommended_path", [])]
    context = "\n".join(
        f"  {r['location']}: {r['congestion_level']} ({r['vehicle_count']} vehicles)"
        for r in relevant
    ) or "  No specific congestion data for route segments."

    prompt = textwrap.dedent(f"""
        A driver wants to go from {start} to {end}.
        The optimal route computed by Dijkstra is: {path_str}
        Total distance: {dist} km | Estimated travel time: {eta} minutes.

        Traffic conditions along the route:
        {context}

        Give a brief, friendly driving tip (2-3 sentences) including:
        - Whether to take this route or wait
        - Any specific road to watch out for
        - An alternate strategy if congestion is HIGH
    """)

    return _call_gemini(
        prompt,
        f"Recommended route: {path_str} ({dist} km, ~{eta} min). Drive safely!"
    )


def generate_emergency_protocol(vehicle_type: str, destination: str, route: list) -> str:
    """Generate AI emergency vehicle instructions."""
    route_str = " → ".join(route)
    prompt = textwrap.dedent(f"""
        An emergency {vehicle_type} needs to reach {destination}.
        Cleared corridor: {route_str}

        Provide a 2-sentence dispatch instruction for traffic control operators,
        including which signals to preempt and estimated corridor clearance time.
    """)
    return _call_gemini(
        prompt,
        f"Emergency {vehicle_type} corridor activated: {route_str}. Clear all intersections immediately."
    )


# ══════════════════════════════════════════════════════════════════════════
#  SIMULATED DATASET GENERATOR (used when no real sensors available)
# ══════════════════════════════════════════════════════════════════════════

LOCATIONS = [
    {"name": "Main Street Junction",     "lat": 30.9010, "lon": 75.8573},
    {"name": "City Center Crossroads",   "lat": 30.9090, "lon": 75.8650},
    {"name": "Airport Road",             "lat": 30.8850, "lon": 75.8400},
    {"name": "Industrial Zone Gate",     "lat": 30.8780, "lon": 75.8700},
    {"name": "University Avenue",        "lat": 30.9200, "lon": 75.8500},
    {"name": "Market Square",            "lat": 30.9150, "lon": 75.8620},
    {"name": "Railway Station Road",     "lat": 30.8950, "lon": 75.8480},
    {"name": "Residential Zone North",   "lat": 30.9300, "lon": 75.8550},
    {"name": "Bus Terminal Approach",    "lat": 30.9050, "lon": 75.8720},
    {"name": "Hospital Road",            "lat": 30.9120, "lon": 75.8590},
]

# Time-of-day congestion profiles
def _time_profile(hour: int) -> str:
    if 8 <= hour <= 10 or 17 <= hour <= 19:   # Rush hours
        return "HIGH"
    if 11 <= hour <= 16:                        # Midday
        return "MEDIUM"
    return "LOW"


def generate_simulated_dataset(n_records: int = 50) -> list:
    """
    Generate realistic simulated traffic sensor readings.
    Used as the RAG knowledge base when real sensors aren't deployed.
    """
    records = []
    now = datetime.utcnow()

    for i in range(n_records):
        loc = random.choice(LOCATIONS)
        # Vary timestamp over last 2 hours
        ts = now - timedelta(minutes=random.randint(0, 120))
        hour = ts.hour

        base_profile = _time_profile(hour)
        # Add some randomness around the base profile
        if base_profile == "HIGH":
            density = random.uniform(75, 120)
            speed   = random.uniform(5, 25)
            count   = random.randint(80, 200)
        elif base_profile == "MEDIUM":
            density = random.uniform(35, 80)
            speed   = random.uniform(25, 50)
            count   = random.randint(30, 90)
        else:
            density = random.uniform(5, 40)
            speed   = random.uniform(50, 80)
            count   = random.randint(5, 35)

        records.append({
            "location":      loc["name"],
            "vehicle_count": count,
            "speed":         round(speed, 1),
            "density":       round(density, 1),
            "timestamp":     ts.isoformat(),
            "latitude":      loc["lat"] + random.uniform(-0.001, 0.001),
            "longitude":     loc["lon"] + random.uniform(-0.001, 0.001),
        })

    return records


def generate_sample_routes() -> list:
    """Generate a mesh of sample routes between intersections."""
    location_names = [loc["name"] for loc in LOCATIONS]
    routes = []
    pairs = []
    for i in range(len(location_names)):
        for j in range(i + 1, len(location_names)):
            if random.random() < 0.5:   # ~50% connectivity
                pairs.append((location_names[i], location_names[j]))

    statuses = ["LOW", "LOW", "MEDIUM", "HIGH"]
    for start, end in pairs:
        routes.append({
            "start_point":   start,
            "end_point":     end,
            "distance":      round(random.uniform(0.5, 8.0), 2),
            "travel_time":   round(random.uniform(2, 20), 1),
            "traffic_status": random.choice(statuses),
        })
    return routes
