"""
Smart Traffic Management System - Database Models
Defines ORM models for all core entities.
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db


class User(db.Model):
    """
    User model for authentication and RBAC.
    """
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="user")  # 'admin' or 'user'
    selected_route = db.Column(db.String(200), default="")  # Storing a selected route e.g., 'A to B'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "selected_route": self.selected_route
        }

class TrafficData(db.Model):
    """
    Stores real-time traffic sensor readings.
    Captures vehicle count, speed, density per location.
    """
    __tablename__ = "traffic_data"

    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100), nullable=False)
    vehicle_count = db.Column(db.Integer, nullable=False, default=0)
    speed = db.Column(db.Float, nullable=False, default=0.0)       # km/h
    density = db.Column(db.Float, nullable=False, default=0.0)     # vehicles/km
    congestion_level = db.Column(db.String(10), default="LOW")     # LOW / MEDIUM / HIGH
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "location": self.location,
            "vehicle_count": self.vehicle_count,
            "speed": self.speed,
            "density": self.density,
            "congestion_level": self.congestion_level,
            "timestamp": self.timestamp.isoformat(),
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


class Signal(db.Model):
    """
    Represents a traffic signal at an intersection.
    Timing is dynamically adjusted based on congestion.
    """
    __tablename__ = "signals"

    signal_id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100), nullable=False)
    green_time = db.Column(db.Integer, default=30)   # seconds
    red_time = db.Column(db.Integer, default=30)     # seconds
    status = db.Column(db.String(10), default="GREEN")  # GREEN / RED / YELLOW
    mode = db.Column(db.String(15), default="NORMAL")   # NORMAL / ADAPTIVE / EMERGENCY
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "signal_id": self.signal_id,
            "location": self.location,
            "green_time": self.green_time,
            "red_time": self.red_time,
            "status": self.status,
            "mode": self.mode,
            "last_updated": self.last_updated.isoformat(),
        }


class Route(db.Model):
    """
    Stores route information between intersections.
    Used by Dijkstra's algorithm for route recommendations.
    """
    __tablename__ = "routes"

    route_id = db.Column(db.Integer, primary_key=True)
    start_point = db.Column(db.String(100), nullable=False)
    end_point = db.Column(db.String(100), nullable=False)
    distance = db.Column(db.Float, default=1.0)           # km
    travel_time = db.Column(db.Float, default=5.0)        # minutes
    traffic_status = db.Column(db.String(10), default="LOW")
    is_recommended = db.Column(db.Boolean, default=True)
    via_points = db.Column(db.Text, default="")           # JSON list of waypoints

    def update_dynamic_travel_time(self):
        """Dynamically adjust travel time based on current congestion and distance."""
        speed_mapping = {"LOW": 50.0, "MEDIUM": 25.0, "HIGH": 12.0} # km/h
        speed = speed_mapping.get(self.traffic_status, 50.0)
        self.travel_time = round((self.distance / speed) * 60, 2)

    def to_dict(self):
        return {
            "route_id": self.route_id,
            "start_point": self.start_point,
            "end_point": self.end_point,
            "distance": self.distance,
            "travel_time": self.travel_time,
            "traffic_status": self.traffic_status,
            "is_recommended": self.is_recommended,
            "via_points": self.via_points,
        }


class Report(db.Model):
    """
    Stores system-generated traffic reports and alerts.
    Used for monitoring and authority notifications.
    """
    __tablename__ = "reports"

    report_id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100), nullable=False)
    congestion_level = db.Column(db.String(10), nullable=False)
    vehicle_count = db.Column(db.Integer, default=0)
    avg_speed = db.Column(db.Float, default=0.0)
    alert_message = db.Column(db.Text, default="")
    ai_analysis = db.Column(db.Text, default="")          # Gemini AI insight
    generated_time = db.Column(db.DateTime, default=datetime.utcnow)
    is_emergency = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "report_id": self.report_id,
            "location": self.location,
            "congestion_level": self.congestion_level,
            "vehicle_count": self.vehicle_count,
            "avg_speed": self.avg_speed,
            "alert_message": self.alert_message,
            "ai_analysis": self.ai_analysis,
            "generated_time": self.generated_time.isoformat(),
            "is_emergency": self.is_emergency,
        }


class EmergencyVehicle(db.Model):
    """
    Tracks emergency vehicle dispatch and priority routing.
    """
    __tablename__ = "emergency_vehicles"

    id = db.Column(db.Integer, primary_key=True)
    vehicle_type = db.Column(db.String(50), default="Ambulance")
    current_location = db.Column(db.String(100))
    destination = db.Column(db.String(100))
    status = db.Column(db.String(20), default="ACTIVE")
    priority_route = db.Column(db.Text, default="")
    dispatched_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "vehicle_type": self.vehicle_type,
            "current_location": self.current_location,
            "destination": self.destination,
            "status": self.status,
            "priority_route": self.priority_route,
            "dispatched_at": self.dispatched_at.isoformat(),
        }
