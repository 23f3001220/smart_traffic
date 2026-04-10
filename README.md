# 🚦 Smart Traffic Management System (STMS)

A full-stack, AI-powered web application for real-time traffic monitoring, adaptive signal control, route optimization, and emergency vehicle dispatch — powered by **Gemini AI (RAG)** and **Dijkstra's algorithm**.

---

## 📁 Project Structure

```
smart_traffic/
├── app.py                          # Flask application entry point
├── extensions.py                   # Shared SQLAlchemy instance
├── requirements.txt
├── models/
│   └── models.py                   # ORM models (TrafficData, Signal, Route, Report, Emergency)
├── routes/
│   ├── traffic_routes.py           # /api/traffic-data endpoints
│   └── api_routes.py               # /api/analyze, /signals, /routes, /reports, /emergency, /ai-insight
├── services/
│   ├── traffic_analysis.py         # Congestion classifier + Dijkstra algorithm
│   └── gemini_service.py           # Gemini AI + RAG pipeline + dataset generator
├── templates/
│   ├── dashboard.html              # Main live dashboard
│   ├── signals.html                # Signal control page
│   ├── routes.html                 # Route planner page
│   ├── reports.html                # Reports & alerts page
│   ├── emergency.html              # Emergency dispatch page
│   └── uml_diagrams.html           # UML & DFD diagrams
└── data/
    └── sample_traffic_data.csv     # Sample dataset
```

---

## ⚙️ Setup & Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Set Gemini API key for AI features
```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
```
> Without the key, all traffic logic still works. Only AI insights/advice are disabled.

### 3. Run the server
```bash
python app.py
```

### 4. Open in browser
```
http://localhost:5000
```

---

## 🌐 Pages

| URL | Description |
|-----|-------------|
| `/` | Live dashboard with heatmap, stats, AI insight |
| `/signals` | Signal control panel with adaptive timing |
| `/routes-page` | Dijkstra route planner with AI travel advice |
| `/reports-page` | Traffic reports and authority alerts |
| `/emergency-page` | Emergency vehicle dispatch with corridor preemption |
| `/uml` | UML & DFD system design diagrams |

---

## 🔌 REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/traffic-data` | Get all traffic readings |
| POST | `/api/traffic-data` | Ingest single sensor reading |
| POST | `/api/traffic-data/simulate?n=50` | Generate simulated dataset |
| GET | `/api/traffic-data/summary` | Aggregate statistics |
| GET | `/api/analyze` | Analyze congestion for all locations |
| GET | `/api/analyze/<location>` | Deep-dive for one location |
| GET | `/api/signal-control` | List all signals |
| POST | `/api/signal-control/update-all` | Sync signal timings with traffic data |
| PUT | `/api/signal-control/<id>` | Manual signal override |
| GET | `/api/routes` | List all route segments |
| GET | `/api/routes/recommend?start=A&end=B` | Dijkstra optimal route + AI advice |
| GET | `/api/routes/locations` | Distinct location names |
| POST | `/api/routes/seed` | Seed sample routes |
| GET | `/api/reports` | List all reports |
| POST | `/api/reports/generate` | Generate fresh reports |
| GET | `/api/emergency` | Dispatch log |
| POST | `/api/emergency` | Dispatch emergency vehicle |
| GET | `/api/ai-insight` | Gemini RAG full analysis |

---

## 🧠 Algorithm & Logic

### Congestion Classification (Threshold-Based)
```python
IF density > 80 veh/km  → congestion = HIGH
ELIF density > 40 veh/km → congestion = MEDIUM
ELIF speed < 15 km/h    → congestion = HIGH   (speed override)
ELIF speed < 30 km/h    → congestion = MEDIUM
ELSE                     → congestion = LOW
```

### Adaptive Signal Timing
```python
HIGH   → green=60s, red=20s   # Drain the queue
MEDIUM → green=45s, red=30s   # Balanced
LOW    → green=30s, red=45s   # Favour cross traffic
```

### Route Recommendation — Dijkstra's Algorithm
- **Graph**: Intersections = nodes, road segments = weighted edges
- **Edge weight** = `travel_time × congestion_multiplier`
  - LOW → ×1.0, MEDIUM → ×1.8, HIGH → ×3.5
- **Output**: Shortest weighted path from source to destination
- **AI augmentation**: Gemini generates natural-language travel advice

### Gemini AI + RAG Pipeline
1. **Retrieve**: Latest 50 traffic records, signal states, active alerts
2. **Augment**: Format as structured context block in the prompt
3. **Generate**: Gemini produces executive summary, action items, trend prediction

---

## 🗄️ Database Schema (SQLite)

```sql
TrafficData(id, location, vehicle_count, speed, density,
            congestion_level, timestamp, latitude, longitude)

Signals(signal_id, location, green_time, red_time,
        status, mode, last_updated)

Routes(route_id, start_point, end_point, distance,
       travel_time, traffic_status, is_recommended, via_points)

Reports(report_id, location, congestion_level, vehicle_count,
        avg_speed, alert_message, ai_analysis, generated_time, is_emergency)

EmergencyVehicles(id, vehicle_type, current_location, destination,
                  status, priority_route, dispatched_at)
```

---

## 🚀 Quick Demo Workflow

1. Click **"⚡ Simulate Data"** on the dashboard sidebar
2. Click **"🔄 Sync Signals"** to update all signal timings
3. Click **"📤 Gen Reports"** to generate authority reports
4. Navigate to **Routes** → Seed routes → Select start/end → Find Route
5. Navigate to **Emergency** → Dispatch an ambulance
6. Click **"🤖 AI Analysis"** for Gemini RAG insight (requires API key)

---

## 🏗️ Design Documents

Visit `/uml` for:
- Use Case Diagram
- Class Diagram
- Activity Diagram
- DFD Level 0 (Context)
- DFD Level 1 (Process Decomposition)
