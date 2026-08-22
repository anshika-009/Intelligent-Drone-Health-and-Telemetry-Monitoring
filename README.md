# IDHTM — Intelligent Drone Health & Telemetry Monitor

IDHTM is a light-first aerospace operations workspace that turns drone telemetry into explainable health intelligence, alerts, recommendations, and operational action.

> Telemetry → Information → Understanding → Decision → Action

The repository contains the supplied visual assets under `frontend/public/assets/images/`, a React + TypeScript operator experience, and a Python + FastAPI telemetry service with a local simulator. The product is rule-based today and exposes clear service boundaries for future anomaly detection, fault prediction, predictive maintenance, and intelligent health scoring.

## Architecture

The frontend is organized around public routes, authentication, a protected application shell, feature pages, a typed API service layer, and a state provider for selected aircraft, simulator state, telemetry, health, alerts, notifications, and user session state. The backend separates API endpoints, schemas, health rules, simulator logic, persistence, and security utilities. The simulator emits the same normalized telemetry shape that a future Pixhawk / MAVLink adapter can use.

The local demo persistence layer uses SQLite so the project starts without additional database setup. Docker Compose also includes PostgreSQL as the production-oriented database service and a clear environment boundary for moving persistence from the demo adapter to PostgreSQL-backed repositories.

## Local development

### Frontend

```bash
cd frontend
pnpm install
pnpm dev
```

Open `http://localhost:5173`. The frontend remains demo-capable when the API is unavailable; when FastAPI is running it connects to `/ws/telemetry` and uses the backend stream.

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`. Health check: `GET /api/healthcheck`. Interactive OpenAPI documentation is available at `/docs`.

### Simulator

The simulator is available in the application dashboard. Choose a scenario from the scenario control, then start or pause the feed. Supported scenarios are Normal Flight, Low Battery, GPS Loss, Signal Degradation, Motor Vibration, and Multi-Fault. Each scenario changes actual telemetry and produces rule-based health and alert output.

Demo credentials are intentionally simple for local development: any valid email and a password with at least six characters are accepted by the UI fallback. The backend seeds `operator@idhtm.dev` with password `demo-flight`.

## Docker

```bash
docker compose up --build
```

This starts PostgreSQL on port `5432`, FastAPI on port `8000`, and the Vite frontend on port `5173`.

## Application routes

Public routes include `/`, `/product`, `/how-it-works`, `/architecture`, `/future-ai`, `/login`, and `/register`. Protected routes include `/app/dashboard`, `/app/cockpit`, `/app/health`, `/app/alerts`, `/app/flights`, `/app/flights/:flightId`, `/app/maintenance`, `/app/reports`, `/app/connections`, and `/app/settings`.

## API surface

The backend exposes `/api/auth`, `/api/drones`, `/api/telemetry`, `/api/health`, `/api/alerts`, `/api/flights`, `/api/maintenance`, `/api/reports`, `/api/connections`, and the real-time `/ws/telemetry` channel. The API uses Pydantic validation, explainable rule metadata, honest source states, and human-readable errors.

## Testing

```bash
cd backend
python3 -m pytest -q tests
cd ../frontend
pnpm build
```

The current backend tests cover low-battery and GPS-loss rule behavior. The frontend production build validates route/component TypeScript integration.

## Design principles

IDHTM uses supplied imagery as the physical world and React-rendered UI as the intelligence layer. The default visual mode is light, with a darker high-contrast cockpit surface only where aviation instrumentation benefits from it. Status colors communicate health state rather than decorate the interface. Future AI capabilities are labeled as planned and are not represented as currently implemented.
