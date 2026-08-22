# Implemented IDHTM Architecture

## Runtime flow

The simulator emits a normalized event containing aircraft identity, flight identity, timestamp, position, altitude, speed, heading, flight mode, battery, signal, GPS, vibration, temperature, motor outputs, and derived health score. The FastAPI service can stream that event over `/ws/telemetry`, persist the selected telemetry fields to SQLite for the local demo, evaluate explainable rule conditions, and return the current alert set.

The frontend connects to the WebSocket when the backend is available. If the API is not running, it falls back to the same scenario-aware local simulator so the demo remains usable without hardware. A scenario selection is sent to the backend when possible and always updates the local state immediately.

## Service boundaries

The current implementation keeps the health rules in `backend/app/services/health/engine.py`, simulator behavior in `backend/app/services/telemetry/simulator.py`, persistence in `backend/app/database/session.py`, validation in `backend/app/schemas/telemetry.py`, and password handling in `backend/app/core/security.py`. The HTTP layer in `backend/app/main.py` exposes predictable endpoint groups and a WebSocket transport. These boundaries are ready to be split into dedicated routers and repositories as the production database adapter grows.

## Truthful system state

The simulator is labeled `SIMULATOR ACTIVE` in the UI and API. Pixhawk / MAVLink and ArduPilot SITL are shown as available compatibility boundaries, not falsely connected hardware. Future AI is described as planned and the active health engine remains explicitly rule-based.

## Data shape

SQLite stores a time-series-friendly telemetry table with timestamp, scenario, health score, battery, signal, GPS fix, and vibration columns, plus a maintenance table for actionable records. The schema is intentionally relational for the local demo. PostgreSQL is included in Docker Compose as the production-oriented database service boundary.
