"""
/traffic-data  –  Traffic Data Collection Module API
"""

from datetime import datetime
from flask import Blueprint, request, jsonify
from extensions import db
from models.models import TrafficData, Report, Route
from services.traffic_analysis import classify_congestion, generate_alert
from services.gemini_service import generate_simulated_dataset

traffic_bp = Blueprint("traffic", __name__)


@traffic_bp.route("/traffic-data", methods=["GET"])
def get_traffic_data():
    """Return paginated traffic readings, optionally filtered by location."""
    location = request.args.get("location")
    limit    = min(int(request.args.get("limit", 50)), 200)
    query    = TrafficData.query.order_by(TrafficData.timestamp.desc())
    if location:
        query = query.filter(TrafficData.location.ilike(f"%{location}%"))
    records = query.limit(limit).all()
    return jsonify({"count": len(records), "data": [r.to_dict() for r in records]})


@traffic_bp.route("/traffic-data", methods=["POST"])
def ingest_traffic_data():
    """
    Ingest a single sensor reading.
    Body: { location, vehicle_count, speed, density, latitude?, longitude? }
    """
    body = request.get_json(force=True)
    congestion = classify_congestion(
        body.get("vehicle_count", 0),
        body.get("speed", 0),
        body.get("density", 0),
    )
    record = TrafficData(
        location      = body["location"],
        vehicle_count = body["vehicle_count"],
        speed         = body["speed"],
        density       = body["density"],
        congestion_level = congestion,
        latitude      = body.get("latitude"),
        longitude     = body.get("longitude"),
    )
    db.session.add(record)

    # Auto-generate alert report for HIGH congestion
    if congestion == "HIGH":
        alert_msg = generate_alert(
            body["location"], congestion,
            body["vehicle_count"], body["speed"]
        )
        report = Report(
            location        = body["location"],
            congestion_level= congestion,
            vehicle_count   = body["vehicle_count"],
            avg_speed       = body["speed"],
            alert_message   = alert_msg,
            is_emergency    = body["vehicle_count"] > 150,
        )
        db.session.add(report)

    # Dynamically update connected routes whenever new traffic data confirms congestion
    routes_to_update = Route.query.filter(
        (Route.start_point == body["location"]) | (Route.end_point == body["location"])
    ).all()
    for r in routes_to_update:
        r.traffic_status = congestion
        r.update_dynamic_travel_time()

    db.session.commit()
    return jsonify({"message": "Data ingested", "congestion": congestion,
                    "id": record.id}), 201


@traffic_bp.route("/traffic-data/simulate", methods=["POST"])
def simulate_data():
    """
    Populate the database with AI-generated simulated traffic data.
    Uses Gemini dataset generator for realistic time-of-day patterns.
    Query param: ?n=50
    """
    n = min(int(request.args.get("n", 50)), 200)
    dataset = generate_simulated_dataset(n)
    inserted = 0
    for row in dataset:
        congestion = classify_congestion(
            row["vehicle_count"], row["speed"], row["density"]
        )
        record = TrafficData(
            location      = row["location"],
            vehicle_count = row["vehicle_count"],
            speed         = row["speed"],
            density       = row["density"],
            congestion_level = congestion,
            latitude      = row.get("latitude"),
            longitude     = row.get("longitude"),
            timestamp     = datetime.fromisoformat(row["timestamp"]),
        )
        db.session.add(record)
        inserted += 1

        # Adjust travel time based on congestion and distance dynamically
        routes_to_update = Route.query.filter(
            (Route.start_point == row["location"]) | (Route.end_point == row["location"])
        ).all()
        for r in routes_to_update:
            r.traffic_status = congestion
            r.update_dynamic_travel_time()

    db.session.commit()
    return jsonify({"message": f"Simulated {inserted} records", "count": inserted}), 201


@traffic_bp.route("/traffic-data/summary", methods=["GET"])
def traffic_summary():
    """Aggregate summary: counts by congestion level."""
    total = TrafficData.query.count()
    high   = TrafficData.query.filter_by(congestion_level="HIGH").count()
    medium = TrafficData.query.filter_by(congestion_level="MEDIUM").count()
    low    = TrafficData.query.filter_by(congestion_level="LOW").count()

    # Average speed across all records
    from sqlalchemy import func
    avg_speed = db.session.query(func.avg(TrafficData.speed)).scalar() or 0
    avg_count = db.session.query(func.avg(TrafficData.vehicle_count)).scalar() or 0

    return jsonify({
        "total_records":   total,
        "high_congestion": high,
        "medium_congestion": medium,
        "low_congestion":  low,
        "avg_speed_kmh":   round(avg_speed, 1),
        "avg_vehicle_count": round(avg_count, 1),
    })
