import threading
import time
import random
from datetime import datetime, timedelta

from extensions import db
from models.models import TrafficData, Signal, Route, Report
from services.traffic_analysis import classify_congestion, generate_alert

def _get_signal_status(signal):
    """Calculate the virtual signal status based on its defined cycle and UTC time."""
    # Use signal_id as a stagger offset so all lights don't sync perfectly
    stagger = signal.signal_id * 3 
    now_ts = int(time.time()) + stagger
    
    yellow_time = 3
    cycle_time = signal.green_time + yellow_time + signal.red_time + yellow_time
    elapsed = now_ts % cycle_time
    
    if elapsed < signal.green_time:
        return "GREEN"
    elif elapsed < signal.green_time + yellow_time:
        return "YELLOW"
    elif elapsed < signal.green_time + yellow_time + signal.red_time:
        return "RED"
    else:
        return "YELLOW"

def _simulation_loop(app):
    with app.app_context():
        while True:
            # Sleep first to allow DB to stabilize on start
            time.sleep(5)
            
            try:
                # 1. Update Signals (Cycle them)
                all_signals = Signal.query.all()
                for sig in all_signals:
                    # If mode is ADAPTIVE or NORMAL, we auto-cycle the status
                    if sig.mode in ["ADAPTIVE", "NORMAL"]:
                        new_status = _get_signal_status(sig)
                        if sig.status != new_status:
                            sig.status = new_status
                db.session.commit()

                # 2. Update Traffic Data (Create new rows for history/freshness)
                for sig in all_signals:
                    loc = sig.location
                    
                    # Fetch MOST RECENT data to use as base
                    base_traffic = TrafficData.query.filter_by(location=loc).order_by(TrafficData.timestamp.desc()).first()
                    
                    if not base_traffic:
                        # Initial seed for this location if it truly has no data
                        new_count = random.randint(10, 50)
                        lat, lon = (12.9 + random.random()*0.1, 77.5 + random.random()*0.1) # Default dummy coords
                    else:
                        new_count = base_traffic.vehicle_count
                        lat, lon = base_traffic.latitude, base_traffic.longitude

                    # Traffic Delta Logic
                    if sig.status == "RED":
                        # Congestion increases significantly at Red lights
                        new_count += random.randint(5, 12)
                    elif sig.status == "GREEN":
                        # Congestion drains significantly at Green lights
                        new_count -= random.randint(8, 15)
                    else: # YELLOW
                        # Slight increase as people slow down
                        new_count += random.randint(1, 3)

                    # Clamp counts
                    new_count = max(0, min(300, new_count))
                    
                    # Calculate physics-based speed
                    # 60km/h on empty road down to 5km/h in gridlock
                    new_speed = round(max(5.0, 60.0 - (new_count / 3.5)), 1)
                    new_density = round(new_count / 1.5, 1) # Assumed 1.5km segment
                    
                    new_congestion = classify_congestion(new_count, new_speed, new_density)
                    
                    # Create NEW record
                    new_traffic = TrafficData(
                        location=loc,
                        vehicle_count=new_count,
                        speed=new_speed,
                        density=new_density,
                        congestion_level=new_congestion,
                        latitude=lat,
                        longitude=lon,
                        timestamp=datetime.utcnow()
                    )
                    db.session.add(new_traffic)
                    
                    # Occasionally generate a report if it's HIGH congestion
                    if new_congestion == "HIGH" and random.random() > 0.7:
                        alert = generate_alert(loc, new_congestion, new_count, new_speed)
                        db.session.add(Report(
                            location=loc,
                            congestion_level=new_congestion,
                            vehicle_count=new_count,
                            avg_speed=new_speed,
                            alert_message=alert,
                            generated_time=datetime.utcnow()
                        ))

                db.session.commit()

                # 3. Update Route Costs
                all_routes = Route.query.all()
                for route in all_routes:
                    # Look up latest traffic for start/end
                    s_t = TrafficData.query.filter_by(location=route.start_point).order_by(TrafficData.timestamp.desc()).first()
                    e_t = TrafficData.query.filter_by(location=route.end_point).order_by(TrafficData.timestamp.desc()).first()
                    
                    if s_t and e_t:
                        # Logic: High congestion on either end slows the whole route
                        if s_t.congestion_level == "HIGH" or e_t.congestion_level == "HIGH":
                            route.traffic_status = "HIGH"
                        elif s_t.congestion_level == "MEDIUM" or e_t.congestion_level == "MEDIUM":
                            route.traffic_status = "MEDIUM"
                        else:
                            route.traffic_status = "LOW"
                        
                        route.update_dynamic_travel_time()
                
                db.session.commit()
                
            except Exception as e:
                print(f"[SIMULATION ERROR] {e}")
                db.session.rollback()

def start_simulation(app):
    """Start the background daemon thread to run the simulation."""
    thread = threading.Thread(target=_simulation_loop, args=(app,), daemon=True)
    thread.start()
