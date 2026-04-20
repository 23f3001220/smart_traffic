"""
Smart Traffic Management System – Main Application Entry Point
=============================================================
Run:  python app.py
Then: open http://localhost:5000
"""

import os
import random
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
                return redirect(url_for('index'))
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
            return render_template('landing.html')
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))

    @app.route("/admin_login", methods=["GET", "POST"])
    def admin_login():
        if request.method == "POST":
            login_id = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            user = User.query.filter((User.username == login_id) | (User.email == login_id)).first()
            if user and user.check_password(password) and user.role == 'admin':
                session['user_id'] = user.id
                session['role'] = user.role
                return redirect(url_for('index'))
            return render_template("auth/admin_login.html", error="Invalid admin credentials")
        return render_template("auth/admin_login.html")

    @app.route("/user_login", methods=["GET", "POST"])
    def user_login():
        if request.method == "POST":
            login_id = request.form.get("username", "").strip() 
            password = request.form.get("password", "")
            user = User.query.filter((User.username == login_id) | (User.email == login_id)).first()
            if user and user.check_password(password) and user.role == 'user':
                session['user_id'] = user.id
                session['role'] = user.role
                return redirect(url_for('index'))
            return render_template("auth/user_login.html", error="Invalid commuter credentials")
        return render_template("auth/user_login.html")

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            username = request.form.get("username", "").strip()
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            
            if not username or not password or not email:
                return render_template("auth/register.html", error="Username, Email, and Password are required")
                
            existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
            if existing_user:
                return render_template("auth/register.html", error="Username or Email already exists")
                
            # Generate OTP
            otp = str(random.randint(100000, 999999))
            print("=" * 40)
            print(f" OTP FOR REGISTRATION ({username}): {otp}")
            print("=" * 40)
            
            # Store in session
            session['register_data'] = {
                'username': username,
                'email': email,
                'password': password,
                'otp': otp
            }
            
            return redirect(url_for('register_otp'))
        return render_template("auth/register.html")

    @app.route("/register_otp", methods=["GET", "POST"])
    def register_otp():
        if 'register_data' not in session:
            return redirect(url_for('register'))
            
        if request.method == "POST":
            submitted_otp = request.form.get("otp", "").strip()
            reg_data = session['register_data']
            
            if submitted_otp == reg_data['otp']:
                new_user = User(username=reg_data['username'], email=reg_data.get('email'), role="user")
                new_user.set_password(reg_data['password'])
                db.session.add(new_user)
                db.session.commit()
                
                # Clear session
                session.pop('register_data', None)
                return redirect(url_for('user_login'))
            else:
                return render_template("auth/register_otp.html", error="Invalid OTP")
                
        return render_template("auth/register_otp.html")

    @app.route("/forgot_password", methods=["GET", "POST"])
    def forgot_password():
        if request.method == "POST":
            login_id = request.form.get("username", "").strip()
            user = User.query.filter((User.username == login_id) | (User.email == login_id)).first()
            
            if user:
                otp = str(random.randint(100000, 999999))
                print("=" * 40)
                print(f" OTP FOR PASSWORD RESET ({user.username}): {otp}")
                print("=" * 40)
                
                session['reset_data'] = {
                    'username': user.username,
                    'otp': otp
                }
                return redirect(url_for('reset_password'))
            else:
                return render_template("auth/forgot_password.html", error="User not found")
                
        return render_template("auth/forgot_password.html")

    @app.route("/reset_password", methods=["GET", "POST"])
    def reset_password():
        if 'reset_data' not in session:
            return redirect(url_for('forgot_password'))
            
        if request.method == "POST":
            submitted_otp = request.form.get("otp", "").strip()
            new_password = request.form.get("password", "")
            reset_data = session['reset_data']
            
            if submitted_otp == reset_data['otp'] and new_password:
                user = User.query.filter_by(username=reset_data['username']).first()
                if user:
                    user.set_password(new_password)
                    db.session.commit()
                    session.pop('reset_data', None)
                    return redirect(url_for('user_login'))
            else:
                return render_template("auth/reset_password.html", error="Invalid OTP or Password missing")
                
        return render_template("auth/reset_password.html")

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for('index'))

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
        admin = User(username="admin", email="admin@stms.com", role="admin")
        admin.set_password("admin")
        db.session.add(admin)
        user = User(username="user1", email="user1@stms.com", role="user")
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
