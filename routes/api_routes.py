"""
Remaining API Blueprints:
  /analyze         – Traffic Analysis Module
  /signal-control  – Signal Control Module
  /routes          – Route Recommendation Module
  /reports         – Monitoring & Reporting Module
  /emergency       – Emergency Vehicle Priority
  /ai-insight      – Gemini RAG analysis
"""

import json
from datetime import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy import func

from extensions import db
from models.models import TrafficData, Signal, Route, Report, EmergencyVehicle
from services.traffic_analysis import (
    classify_congestion, compute_signal_timing,
    recommend_routes, generate_alert
)
from services.gemini_service import (
    analyze_traffic_with_ai, get_ai_route_advice,
    generate_emergency_protocol, generate_sample_routes
)

# ── Blueprints ─────────────────────────────────────────────────────────────
analyze_bp  = Blueprint("analyze",  __name__)
signal_bp   = Blueprint("signals",  __name__)
route_bp    = Blueprint("routes",   __name__)
report_bp   = Blueprint("reports",  __name__)
emergency_bp= Blueprint("emergency",__name__)
ai_bp       = Blueprint("ai",       __name__)


# ══════════════════════════════════════════════════════════════════════════
#  /analyze
# ══════════════════════════════════════════════════════════════════════════

@analyze_bp.route("/analyze", methods=["GET"])
def analyze_all():
    """
    Analyze latest reading per location and return congestion map.
    """
    # Subquery: latest id per location
    latest_ids = (
        db.session.query(func.max(TrafficData.id))
        .group_by(TrafficData.location)
        .all()
    )
    ids = [row[0] for row in latest_ids if row[0]]
    records = TrafficData.query.filter(TrafficData.id.in_(ids)).all()

    results = []
    for r in records:
        congestion = classify_congestion(r.vehicle_count, r.speed, r.density)
        timing     = compute_signal_timing(congestion)
        results.append({
            "location":        r.location,
            "latitude":        r.latitude,
            "longitude":       r.longitude,
            "congestion_level": congestion,
            "vehicle_count":   r.vehicle_count,
            "speed_kmh":       r.speed,
            "density":         r.density,
            "recommended_green_time": timing["green"],
            "recommended_red_time":   timing["red"],
            "timestamp":       r.timestamp.isoformat(),
        })

    high_count = sum(1 for r in results if r["congestion_level"] == "HIGH")
    return jsonify({
        "analyzed_locations": len(results),
        "high_congestion_zones": high_count,
        "analysis": results,
    })


@analyze_bp.route("/analyze/<location>", methods=["GET"])
def analyze_location(location):
    """Deep-dive analysis for a single location."""
    record = (TrafficData.query
              .filter(TrafficData.location.ilike(f"%{location}%"))
              .order_by(TrafficData.timestamp.desc())
              .first())
    if not record:
        return jsonify({"error": "Location not found"}), 404

    congestion = classify_congestion(record.vehicle_count, record.speed, record.density)
    timing     = compute_signal_timing(congestion)
    alert      = generate_alert(record.location, congestion, record.vehicle_count, record.speed)
    return jsonify({
        "location":        record.location,
        "latitude":        record.latitude,
        "longitude":       record.longitude,
        "congestion_level": congestion,
        "vehicle_count":   record.vehicle_count,
        "speed_kmh":       record.speed,
        "density":         record.density,
        "signal_timing":   timing,
        "alert":           alert,
        "timestamp":       record.timestamp.isoformat(),
    })


# ══════════════════════════════════════════════════════════════════════════
#  /signal-control
# ══════════════════════════════════════════════════════════════════════════

@signal_bp.route("/signal-control", methods=["GET"])
def get_signals():
    """Return all traffic signals and their current state."""
    signals = Signal.query.all()
    return jsonify({"count": len(signals), "signals": [s.to_dict() for s in signals]})


@signal_bp.route("/signal-control/update-all", methods=["POST"])
def update_all_signals():
    """
    Auto-update all signal timings based on latest traffic data.
    Triggered by the dashboard 'Sync Signals' button.
    """
    # Latest record per location
    latest_ids = (
        db.session.query(func.max(TrafficData.id))
        .group_by(TrafficData.location)
        .all()
    )
    ids = [row[0] for row in latest_ids if row[0]]
    records = TrafficData.query.filter(TrafficData.id.in_(ids)).all()
    updated = 0

    for r in records:
        congestion = classify_congestion(r.vehicle_count, r.speed, r.density)
        timing     = compute_signal_timing(congestion)
        signal = Signal.query.filter(Signal.location == r.location).first()
        if not signal:
            signal = Signal(location=r.location)
            db.session.add(signal)
        signal.green_time   = timing["green"]
        signal.red_time     = timing["red"]
        signal.mode         = "ADAPTIVE"
        signal.last_updated = datetime.utcnow()
        updated += 1

    db.session.commit()
    return jsonify({"message": f"Updated {updated} signals", "updated": updated})


@signal_bp.route("/signal-control/<int:signal_id>", methods=["PUT"])
def update_signal(signal_id):
    """Manually override a single signal."""
    signal = Signal.query.get_or_404(signal_id)
    body   = request.get_json(force=True)
    signal.green_time   = body.get("green_time", signal.green_time)
    signal.red_time     = body.get("red_time", signal.red_time)
    signal.status       = body.get("status", signal.status)
    signal.mode         = body.get("mode", signal.mode)
    signal.last_updated = datetime.utcnow()
    db.session.commit()
    return jsonify(signal.to_dict())


# ══════════════════════════════════════════════════════════════════════════
#  /routes
# ══════════════════════════════════════════════════════════════════════════

@route_bp.route("/routes", methods=["GET"])
def get_routes():
    """List all routes."""
    routes = Route.query.all()
    return jsonify({"count": len(routes), "routes": [r.to_dict() for r in routes]})


@route_bp.route("/routes/recommend", methods=["GET"])
def recommend():
    """
    GET /routes/recommend?start=A&end=B
    Returns Dijkstra optimal path with AI travel advice.
    """
    start = request.args.get("start", "").strip()
    end   = request.args.get("end", "").strip()
    if not start or not end:
        return jsonify({"error": "start and end parameters required"}), 400

    # Only pathfind across enabled (recommended) routes
    all_routes = Route.query.filter_by(is_recommended=True).all()
    result     = recommend_routes(all_routes, start, end)

    if "error" in result:
        return jsonify(result), 404

    # Augment with AI advice (RAG)
    traffic_snapshot = [r.to_dict() for r in TrafficData.query
                        .order_by(TrafficData.timestamp.desc()).limit(40).all()]
    result["ai_advice"] = get_ai_route_advice(start, end, result, traffic_snapshot)
    return jsonify(result)


@route_bp.route("/routes/locations", methods=["GET"])
def get_locations():
    """Return distinct location names for route dropdowns."""
    from sqlalchemy import union
    starts = db.session.query(Route.start_point.label("loc")).distinct()
    ends   = db.session.query(Route.end_point.label("loc")).distinct()
    locs   = {row.loc for row in starts.union(ends).all()}
    return jsonify(sorted(locs))


@route_bp.route("/routes/seed", methods=["POST"])
def seed_routes():
    """Seed sample routes using AI-generated dataset."""
    if Route.query.count() > 0:
        return jsonify({"message": "Routes already seeded"}), 200
    sample = generate_sample_routes()
    for r in sample:
        route_obj = Route(**r)
        route_obj.update_dynamic_travel_time()
        db.session.add(route_obj)
    db.session.commit()
    return jsonify({"message": f"Seeded {len(sample)} routes"}), 201

@route_bp.route("/routes/<int:route_id>/toggle", methods=["PUT"])
def toggle_route(route_id):
    """Toggle the is_recommended status of a specific route (admin control)."""
    route = Route.query.get_or_404(route_id)
    body = request.get_json(force=True)
    if "is_recommended" in body:
        route.is_recommended = body["is_recommended"]
    else:
        route.is_recommended = not route.is_recommended
    db.session.commit()
    return jsonify(route.to_dict())


# ══════════════════════════════════════════════════════════════════════════
#  /reports
# ══════════════════════════════════════════════════════════════════════════

@report_bp.route("/reports", methods=["GET"])
def get_reports():
    """Return reports, newest first. Optional filter: ?emergency=true, ?location=..., ?timeframe=..."""
    from datetime import datetime, timedelta
    emergency = request.args.get("emergency")
    location = request.args.get("location")
    timeframe = request.args.get("timeframe", "24h")

    query = Report.query.order_by(Report.generated_time.desc())
    if emergency == "true":
        query = query.filter_by(is_emergency=True)
    if location:
        query = query.filter(Report.location.ilike(f"%{location}%"))

    now = datetime.utcnow()
    if timeframe == "24h":
        query = query.filter(Report.generated_time >= now - timedelta(hours=24))
    elif timeframe == "48h":
        query = query.filter(Report.generated_time >= now - timedelta(hours=48))
    elif timeframe == "5d":
        query = query.filter(Report.generated_time >= now - timedelta(days=5))
    elif timeframe == "7d":
        query = query.filter(Report.generated_time >= now - timedelta(days=7))

    reports = query.limit(200).all()
    return jsonify({"count": len(reports), "reports": [r.to_dict() for r in reports]})


@report_bp.route("/reports/generate", methods=["POST"])
def generate_reports():
    """
    Generate fresh reports for all locations based on latest traffic data.
    """
    latest_ids = (
        db.session.query(func.max(TrafficData.id))
        .group_by(TrafficData.location).all()
    )
    ids = [row[0] for row in latest_ids if row[0]]
    records = TrafficData.query.filter(TrafficData.id.in_(ids)).all()
    created = 0
    for r in records:
        congestion = classify_congestion(r.vehicle_count, r.speed, r.density)
        alert_msg  = generate_alert(r.location, congestion, r.vehicle_count, r.speed)
        report = Report(
            location        = r.location,
            congestion_level= congestion,
            vehicle_count   = r.vehicle_count,
            avg_speed       = r.speed,
            alert_message   = alert_msg,
            is_emergency    = (congestion == "HIGH" and r.vehicle_count > 150),
        )
        db.session.add(report)
        created += 1
    db.session.commit()
    return jsonify({"message": f"Generated {created} reports", "count": created})


# ══════════════════════════════════════════════════════════════════════════
#  /emergency
# ══════════════════════════════════════════════════════════════════════════

@emergency_bp.route("/emergency", methods=["GET"])
def get_emergencies():
    return jsonify([e.to_dict() for e in EmergencyVehicle.query.all()])


@emergency_bp.route("/emergency", methods=["POST"])
def dispatch_emergency():
    """
    Dispatch an emergency vehicle and clear signal corridors.
    Body: { vehicle_type, current_location, destination }
    """
    body = request.get_json(force=True)
    v_type  = body.get("vehicle_type", "Ambulance")
    current = body.get("current_location", "")
    dest    = body.get("destination", "")

    # Find path
    all_routes  = Route.query.all()
    path_result = recommend_routes(all_routes, current, dest)
    path        = path_result.get("recommended_path", [current, dest])

    # Set all signals on path to GREEN (emergency preemption)
    for loc in path:
        sig = Signal.query.filter(Signal.location == loc).first()
        if sig:
            sig.status = "GREEN"
            sig.mode   = "EMERGENCY"
            sig.green_time = 90
    db.session.commit()

    ev = EmergencyVehicle(
        vehicle_type     = v_type,
        current_location = current,
        destination      = dest,
        priority_route   = json.dumps(path),
    )
    db.session.add(ev)
    db.session.commit()

    ai_msg = generate_emergency_protocol(v_type, dest, path)
    return jsonify({
        "message":        "Emergency vehicle dispatched",
        "corridor":       path,
        "ai_instruction": ai_msg,
        "vehicle_id":     ev.id,
    }), 201


# ══════════════════════════════════════════════════════════════════════════
#  /ai-insight  (RAG endpoint)
# ══════════════════════════════════════════════════════════════════════════

@ai_bp.route("/ai-insight", methods=["GET"])
def ai_insight():
    """
    Full RAG pipeline: retrieves latest data → augments Gemini prompt → returns insight.
    """
    traffic_records = [r.to_dict() for r in
                       TrafficData.query.order_by(TrafficData.timestamp.desc()).limit(50).all()]
    signals  = [s.to_dict() for s in Signal.query.all()]
    reports  = [r.to_dict() for r in Report.query.order_by(Report.generated_time.desc()).limit(20).all()]

    insight = analyze_traffic_with_ai(traffic_records, signals, reports)
    return jsonify({"insight": insight, "generated_at": datetime.utcnow().isoformat()})
