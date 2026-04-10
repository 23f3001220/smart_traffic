"""
Smart Traffic Management System – Main Application Entry Point
=============================================================
Run:  python app.py
Then: open http://localhost:5000
"""

import os
from dotenv import load_dotenv

load_dotenv()  # Load .env file (GEMINI_API_KEY, etc.)

from functools import wraps
from flask import Flask, render_template, jsonify, request, session, redirect, url_for, flash
from flask_cors import CORS

from extensions import db
from models.models import TrafficData, Signal, Route, Report, EmergencyVehicle, User
from routes.traffic_routes import traffic_bp
from routes.api_routes import (
    analyze_bp, signal_bp, route_bp,
    report_bp, emergency_bp, ai_bp
)
from services.simulation_engine import start_simulation


def create_app() -> Flask:
    app = Flask(__name__)

    # ── Configuration ──────────────────────────────────────────────────────
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "stms-secret-2024")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///traffic.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JSON_SORT_KEYS"] = False

    # ── Extensions ─────────────────────────────────────────────────────────
    CORS(app)
    db.init_app(app)

    # ── Blueprints ─────────────────────────────────────────────────────────
    for bp in [traffic_bp, analyze_bp, signal_bp, route_bp,
               report_bp, emergency_bp, ai_bp]:
        app.register_blueprint(bp, url_prefix="/api")

    # ── Authentication Decorators ──────────────────────────────────────────
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function

    def role_required(role):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if session.get('role') != role:
                    return "Forbidden", 403
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    @app.context_processor
    def inject_user():
        user = None
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
        return dict(current_user=user)

    # ── Dashboard & Auth routes ───────────────────────────────────────────
    @app.route("/")
    def index():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                session['user_id'] = user.id
                session['role'] = user.role
                return redirect(url_for('index'))
            return render_template("auth/login.html", error="Invalid credentials")
        return render_template("auth/login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            
            if not username or not password:
                return render_template("auth/register.html", error="Username and Password are required")
                
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return render_template("auth/register.html", error="Username already exists")
                
            new_user = User(username=username, role="user")
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            return redirect(url_for('login'))
        return render_template("auth/register.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for('login'))

    @app.route("/admin_dashboard")
    @login_required
    @role_required("admin")
    def admin_dashboard():
        return render_template("admin_dashboard.html")

    @app.route("/user_dashboard")
    @login_required
    @role_required("user")
    def user_dashboard():
        return render_template("user_dashboard.html")

    @app.route("/signals")
    @login_required
    @role_required("admin")
    def signals_page():
        return render_template("signals.html")

    @app.route("/routes-page")
    @login_required
    @role_required("admin")
    def routes_page():
        return render_template("routes.html")

    @app.route("/reports-page")
    @login_required
    @role_required("admin")
    def reports_page():
        return render_template("reports.html")

    @app.route("/emergency-page")
    @login_required
    @role_required("admin")
    def emergency_page():
        return render_template("emergency.html")

    @app.route("/uml")
    def uml_page():
        return render_template("uml_diagrams.html")

    @app.route("/favicon.ico")
    def favicon():
        return "", 204

    # ── Health check ───────────────────────────────────────────────────────
    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "Smart Traffic Management System"})

    # ── DB Init ────────────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        _seed_signals_if_empty()
        _seed_admin_if_empty()

    # Start the continuous background simulation daemon
    start_simulation(app)

    return app


def _seed_admin_if_empty():
    """Seed initial admin user and a test user."""
    if User.query.count() == 0:
        admin = User(username="admin", role="admin")
        admin.set_password("admin")
        db.session.add(admin)
        user = User(username="user1", role="user")
        user.set_password("password")
        db.session.add(user)
        db.session.commit()



def _seed_signals_if_empty():
    """Pre-populate signals for known intersections."""
    if Signal.query.count() == 0:
        locations = [
            "Main Street Junction", "City Center Crossroads", "Airport Road",
            "Industrial Zone Gate", "University Avenue", "Market Square",
            "Railway Station Road", "Residential Zone North",
            "Bus Terminal Approach", "Hospital Road",
        ]
        for loc in locations:
            db.session.add(Signal(location=loc, green_time=30, red_time=30,
                                  status="GREEN", mode="NORMAL"))
        db.session.commit()


if __name__ == "__main__":
    app = create_app()
    gemini_status = "✅ GEMINI_API_KEY loaded from .env" if os.environ.get("GEMINI_API_KEY") else "⚠️  Set GEMINI_API_KEY in .env to enable AI features"
    print("=" * 60)
    print("  Smart Traffic Management System")
    print("  http://localhost:5000")
    print(f"  {gemini_status}")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)
