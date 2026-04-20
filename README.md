# 🚦 Smart Traffic Management System (STMS)

A full-stack Flask app for traffic monitoring, adaptive signal control, route optimization, emergency dispatch, and optional AI-powered guidance via Gemini.

---

## 📁 Project Structure

```
smart_traffic/
├── app.py                          # Flask application entry point
├── extensions.py                   # Shared SQLAlchemy instance
├── requirements.txt
├── .env                            # Local environment settings
├── models/
│   └── models.py                   # ORM models (TrafficData, Signal, Route, Report, EmergencyVehicle, User)
├── routes/
│   ├── traffic_routes.py           # Traffic ingestion + simulation endpoints
│   └── api_routes.py               # Analyze, signal, route, report, emergency, AI endpoints
├── services/
│   ├── traffic_analysis.py         # Congestion classification + route recommendation logic
│   ├── gemini_service.py           # Gemini AI / RAG integration + dataset generator
│   └── simulation_engine.py        # Background traffic simulation daemon
├── templates/
│   ├── admin_dashboard.html        # Admin dashboard
│   ├── user_dashboard.html         # User dashboard
│   ├── signals.html                # Signal control page
│   ├── routes.html                 # Route planner page
│   ├── reports.html                # Reports page
│   ├── emergency.html              # Emergency dispatch page
│   └── uml_diagrams.html           # System design diagrams
└── data/
    └── sample_traffic_data.csv     # Sample dataset
```

---

## ⚙️ Setup & Run

### 1. Create and activate a virtual environment
```bash
python -m venv venv
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
Create or update `.env` with:
```env
GEMINI_API_KEY=your-gemini-api-key-here
SECRET_KEY=your-secret-key-here
```

> AI features require `GEMINI_API_KEY`. The app works without it, but the AI insight endpoint will return a fallback message.

### 4. Run the application
```bash
python app.py
```

### 5. Open the app
```text
http://localhost:5000
```

---

## 🌐 Pages

| URL | Description |
|-----|-------------|
| `/login` | Login page |
| `/register` | User registration |
| `/admin_dashboard` | Admin dashboard |
| `/user_dashboard` | User dashboard |
| `/signals` | Signal control panel (admin-only) |
| `/routes-page` | Route planner page (admin-only) |
| `/reports-page` | Reports and alerts page (admin-only) |
| `/emergency-page` | Emergency dispatch page (admin-only) |
| `/uml` | UML & DFD diagrams |

> Default credentials: `admin / admin`, `user1 / password`

---

## 🔌 REST API Endpoints

All endpoints are available under `/api`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/traffic-data` | Retrieve traffic readings |
| POST | `/api/traffic-data` | Ingest a traffic reading |
| POST | `/api/traffic-data/simulate?n=50` | Generate simulated traffic data |
| GET | `/api/traffic-data/summary` | Aggregate traffic summary |
| GET | `/api/analyze` | Analyze current congestion across locations |
| GET | `/api/analyze/<location>` | Analyze a single location |
| GET | `/api/signal-control` | List all traffic signals |
| POST | `/api/signal-control/update-all` | Auto-update all signal timings |
| PUT | `/api/signal-control/<signal_id>` | Override a specific signal |
| GET | `/api/routes` | List stored routes |
| GET | `/api/routes/recommend?start=A&end=B` | Recommend optimal route |
| GET | `/api/routes/locations` | List available route locations |
| POST | `/api/routes/seed` | Seed sample routes |
| PUT | `/api/routes/<route_id>/toggle` | Toggle route recommendation status |
| GET | `/api/reports` | Retrieve reports (optional filtering) |
| POST | `/api/reports/generate` | Generate fresh reports |
| GET | `/api/emergency` | Get emergency dispatch log |
| POST | `/api/emergency` | Dispatch an emergency vehicle |
| GET | `/api/ai-insight` | Return Gemini RAG analysis |

---

## 🧠 Core Logic

### Congestion & Signal Control
- Congestion is classified from vehicle count, speed, and density.
- Adaptive signal timing updates green/red durations based on congestion.
- Signals may also be set to `EMERGENCY` mode for priority routes.

### Route Recommendation
- Uses Dijkstra's algorithm to compute the shortest weighted path.
- Weights are adjusted by congestion status for travel-time-aware routing.
- Recommended routes can be augmented with AI travel advice.

### Gemini AI + RAG
- Retrieves latest traffic readings, signal states, and reports.
- Builds structured context for the prompt.
- Generates executive summaries, action items, and route instructions.

---

## 🔐 Authentication & Roles

- Public pages: `/login`, `/register`
- Admin-only pages: `/admin_dashboard`, `/signals`, `/routes-page`, `/reports-page`, `/emergency-page`
- Regular users are redirected to `/user_dashboard` after login.

---

## 🗄️ Database

The app uses SQLite with the database file `traffic.db`.
It is created automatically on first startup.

---

## 🚀 Quick Start

1. Start the app and log in as `admin`
2. Seed sample routes from the Routes page
3. Simulate traffic data from the dashboard
4. Sync signals to update timings
5. Generate reports and view AI insight
6. Dispatch emergency vehicles from the Emergency page
