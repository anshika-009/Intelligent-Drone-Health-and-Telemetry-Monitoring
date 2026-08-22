# IDHTM — Product & Technical Architecture Specification

## 1. Product identity

**Product:** Intelligent Drone Health & Telemetry Monitor (IDHTM)

**Core idea:** Transform raw drone telemetry into meaningful health insights, timely alerts, and operational recommendations.

The architecture supports the current rule-based monitoring requirements while leaving clear extension points for future anomaly detection, fault prediction, predictive maintenance, and intelligent health scoring.

---

## 2. Architecture principles

1. **Modular:** telemetry, health, alerts, flights, maintenance, reporting, and authentication remain independently maintainable.
2. **Real-time ready:** telemetry ingestion and frontend updates must support continuous streams rather than polling-only assumptions.
3. **Simulator-first for development:** the product must work without physical Pixhawk hardware.
4. **Hardware-ready:** real Pixhawk/ArduPilot MAVLink ingestion can replace or coexist with the simulator.
5. **API-first:** the React frontend communicates with FastAPI through typed REST APIs and a real-time telemetry channel.
6. **Database-backed:** flight logs, telemetry, health, alerts, and maintenance history are persistent.
7. **AI-ready, not AI-faked:** future AI capabilities have interfaces and storage boundaries but are not represented as implemented until actually implemented.
8. **Deployment-ready:** Dockerized services with a path toward Raspberry Pi/edge deployment.

---

## 3. Technology stack

### Frontend

- React
- TypeScript
- React Router
- State management appropriate to application complexity
- Charting library appropriate for streaming telemetry
- Mapping library appropriate for GPS visualization
- CSS/design system implemented locally in the application

### Backend

- Python
- FastAPI
- Pydantic
- pymavlink for MAVLink integration
- WebSocket or equivalent real-time transport for live telemetry updates

### Database

- PostgreSQL for production/deployment
- SQLite may be used for lightweight local/demo development

### Infrastructure

- Docker
- Docker Compose for local multi-service development
- Nginx or equivalent reverse proxy where required

### Flight ecosystem

- Pixhawk
- ArduPilot
- MAVLink
- ArduPilot SITL
- QGroundControl / Mission Planner may be used externally for development/testing

---

## 4. High-level architecture

```text
                     ┌───────────────────────┐
                     │       React UI        │
                     │ Public + App Routes   │
                     └───────────┬───────────┘
                                 │
                       REST + Real-time
                                 │
                     ┌───────────▼───────────┐
                     │       FastAPI         │
                     │      API Layer        │
                     └───────────┬───────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼
   Telemetry Service       Health Engine          Alert Engine
          │                      │                      │
          │                      └──────────┬───────────┘
          │                                 │
          ├──────────────► Flight Service    │
          │                                 │
          └──────────────► Database ◄────────┘
                              │
                 ┌────────────┼────────────┐
                 ▼            ▼            ▼
             Flights      Maintenance   Reports

Telemetry sources:

   Pixhawk / ArduPilot ──► MAVLink ──► pymavlink ──► Telemetry Service

   Simulator ─────────────────────────────────────► Telemetry Service
```

---

## 5. Frontend application architecture

### Public routes

```text
/
/product
/how-it-works
/architecture
/future-ai
/login
/register
```

### Authenticated routes

```text
/app
/app/dashboard
/app/cockpit
/app/health
/app/alerts
/app/flights
/app/flights/:flightId
/app/maintenance
/app/reports
/app/connections
/app/settings
```

### Frontend layers

```text
pages
  ↓
layouts
  ↓
feature components
  ↓
common components
  ↓
hooks / services / store
  ↓
API client
```

The UI must never directly construct business logic that belongs in the backend. Formatting and presentation logic may remain in the frontend.

---

## 6. Backend module boundaries

```text
backend/app/
│
├── api/                 # HTTP/WebSocket endpoints
├── core/                # configuration, security, application settings
├── database/            # DB session, initialization, repository support
├── models/              # ORM/database models
├── schemas/             # request/response validation models
├── services/
│   ├── telemetry/       # ingestion, normalization, streaming
│   ├── health/          # health calculations and trends
│   ├── alerts/          # rule evaluation and alert lifecycle
│   ├── flights/         # flight lifecycle/history/replay data
│   ├── maintenance/     # recommendations and maintenance records
│   └── reports/         # report aggregation/generation
├── simulator/           # development/demo telemetry simulator
└── utils/               # small shared utilities only
```

Routes should be thin. Business logic belongs in services.

---

## 7. Telemetry flow

### Simulator mode

```text
Scenario JSON
     ↓
Simulator Engine
     ↓
Normalized Telemetry Event
     ↓
Telemetry Service
     ├── persist selected telemetry
     ├── calculate derived fields
     ├── update health engine
     ├── evaluate alert rules
     └── publish real-time update
             ↓
          Frontend
```

### Hardware mode

```text
Pixhawk / ArduPilot
       ↓
MAVLink
       ↓
pymavlink adapter
       ↓
Normalized Telemetry Event
       ↓
Telemetry Service
       ↓
Health / Alerts / Persistence / Streaming
```

The rest of the system should operate on the normalized event shape, not directly on raw MAVLink messages. This keeps simulator and hardware inputs interchangeable.

---

## 8. Canonical telemetry event

The implementation should define a typed canonical representation containing, where available:

```text
id
 drone_id
 flight_id
 timestamp
 latitude
 longitude
 altitude
 ground_speed
 airspeed
 vertical_speed
 heading
 flight_mode
 battery_percentage
 battery_voltage
 battery_current
 estimated_remaining_flight_time
 signal_strength
 gps_fix
 gps_satellites
 vibration
 temperature
 motor_outputs
 imu_values
```

Not every source will provide every field. Missing measurements must be represented explicitly rather than silently fabricated.

---

## 9. Health engine

The first production-capable health engine is rule-based.

### Components

- Battery
- Motors
- GPS
- Sensors
- Communication signal

### Health output

Each component should produce:

```text
component
score
status
severity
observations
trend
recommendation
updated_at
```

The overall drone health score is derived from component health according to a documented weighting strategy. The exact weights should live in configuration rather than being hard-coded throughout the UI.

---

## 10. Alert engine

Initial rule classes:

```text
LOW_BATTERY
WEAK_SIGNAL
HIGH_VIBRATION
GPS_LOSS
TEMPERATURE_WARNING
RETURN_TO_HOME_RECOMMENDATION
```

Each alert should contain:

```text
id
drone_id
flight_id
rule_code
severity
title
message
triggered_at
acknowledged_at
resolved_at
recommendation
metadata
```

### Severity levels

```text
INFO
WARNING
CRITICAL
```

Alert generation should be deterministic for a given telemetry stream and rule configuration.

---

## 11. Flight lifecycle

A flight represents a telemetry session.

Suggested lifecycle:

```text
PLANNED
  ↓
CONNECTED
  ↓
IN_FLIGHT
  ↓
COMPLETED
```

Abnormal termination may use:

```text
ABORTED
INTERRUPTED
```

A completed flight should be able to reference:

- telemetry history
- health history
- alerts
- flight events
- maintenance recommendations generated during the flight

---

## 12. Flight replay architecture

The replay screen should read recorded telemetry rather than regenerate it.

```text
Stored telemetry
      ↓
Time-ordered flight timeline
      ↓
Replay controller
      ├── map position
      ├── charts
      ├── metrics
      ├── health
      └── alert events
```

Replay controls should support at least:

```text
play / pause
seek
speed: 1x / 2x / 4x
jump to event
```

All synchronized views must use the same replay timestamp.

---

## 13. Maintenance module

Maintenance recommendations originate from health/alert logic and become persisted records only when explicitly created as maintenance tasks.

Suggested maintenance fields:

```text
id
drone_id
source_alert_id
component
title
description
priority
status
created_at
due_at
completed_at
notes
```

Statuses:

```text
PENDING
IN_PROGRESS
COMPLETED
CANCELLED
```

---

## 14. Database entities

Core entities:

```text
users
 drones
flights
telemetry
health_status
alerts
maintenance_records
flight_events
```

The implementation may introduce additional tables such as:

```text
refresh_tokens / sessions
telemetry_sessions
connections
reports
```

where justified.

### Relationship overview

```text
User
 └──< Drone
       └──< Flight
             ├──< Telemetry
             ├──< Health Status
             ├──< Alerts
             └──< Flight Events

Drone
 └──< Maintenance Records
```

---

## 15. REST API surface

Initial endpoint groups:

### Authentication

```text
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
```

### Drones

```text
GET    /api/v1/drones
POST   /api/v1/drones
GET    /api/v1/drones/{drone_id}
PATCH  /api/v1/drones/{drone_id}
DELETE /api/v1/drones/{drone_id}
```

### Telemetry

```text
GET    /api/v1/drones/{drone_id}/telemetry/latest
GET    /api/v1/flights/{flight_id}/telemetry
POST   /api/v1/telemetry/ingest
```

A dedicated real-time channel should expose live normalized telemetry and relevant state changes.

### Health

```text
GET    /api/v1/drones/{drone_id}/health
GET    /api/v1/drones/{drone_id}/health/history
GET    /api/v1/flights/{flight_id}/health
```

### Alerts

```text
GET    /api/v1/alerts
GET    /api/v1/alerts/{alert_id}
POST   /api/v1/alerts/{alert_id}/acknowledge
```

### Flights

```text
GET    /api/v1/flights
GET    /api/v1/flights/{flight_id}
POST   /api/v1/flights/start
POST   /api/v1/flights/{flight_id}/complete
GET    /api/v1/flights/{flight_id}/events
```

### Maintenance

```text
GET    /api/v1/maintenance
POST   /api/v1/maintenance
GET    /api/v1/maintenance/{task_id}
PATCH  /api/v1/maintenance/{task_id}
```

### Reports

```text
GET    /api/v1/reports/flight/{flight_id}
GET    /api/v1/reports/health/{drone_id}
```

Exact schemas, pagination, validation, authentication requirements and error formats must be defined during implementation rather than guessed in the UI.

---

## 16. Real-time transport

The live monitor should use a real-time transport for streaming telemetry. WebSocket is the preferred initial implementation.

Conceptually:

```text
ws://.../api/v1/ws/drones/{drone_id}
```

Server events may include:

```text
telemetry.update
health.update
alert.created
alert.resolved
flight.status_changed
connection.status_changed
```

The frontend should handle temporary disconnection gracefully and show connection state instead of silently freezing data.

---

## 17. Simulator architecture

The simulator must support deterministic demo scenarios.

### Scenarios

```text
normal
low_battery
gps_loss
signal_degradation
motor_vibration
multi_fault
```

Each scenario defines telemetry behavior over time rather than hard-coding scenario behavior into React components.

### Simulator requirements

- configurable update interval
- configurable starting state
- time-based changes
- repeatable scenarios
- ability to stop/reset
- realistic but synthetic values
- ability to trigger the rule engine naturally

The demo UI should make the active scenario visible.

---

## 18. Demo mode

Demo mode is a first-class product capability for presentations.

The operator can select:

```text
NORMAL FLIGHT
LOW BATTERY
GPS LOSS
SIGNAL DEGRADATION
MOTOR VIBRATION
MULTI-FAULT
```

The scenario must cause the same downstream behavior as a real telemetry stream:

```text
Telemetry changes
   ↓
Health changes
   ↓
Alert generated
   ↓
Recommendation generated
   ↓
Dashboard updates
```

The demo must not use hard-coded frontend-only visual tricks that bypass backend logic.

---

## 19. Authentication and authorization

Initial authentication scope:

- registration
- login
- session/token management
- protected application routes
- logout
- current-user endpoint

Authorization can begin with a single authenticated user model. Role-based access should be introduced only when there is a real requirement.

Passwords must never be stored as plaintext.

Secrets must come from environment configuration.

---

## 20. API error contract

Use a consistent error shape such as:

```json
{
  "error": {
    "code": "TELEMETRY_UNAVAILABLE",
    "message": "Live telemetry is currently unavailable.",
    "details": null,
    "request_id": "..."
  }
}
```

Frontend behavior should distinguish:

- validation errors
- authentication errors
- connection errors
- missing resources
- server errors
- telemetry-source failures

---

## 21. Configuration

Configuration belongs in environment variables or typed settings.

Examples:

```text
DATABASE_URL
JWT_SECRET / equivalent secret
CORS_ORIGINS
API_BASE_URL
TELEMETRY_MODE
MAVLINK_CONNECTION_STRING
SIMULATOR_UPDATE_INTERVAL
```

`.env.example` documents required variables without containing secrets.

---

## 22. Docker architecture

Local development should support a compose stack conceptually containing:

```text
frontend
backend
postgres
nginx (where needed)
```

The simulator may run inside the backend initially. It can become a separate service later if load or deployment architecture requires it.

---

## 23. Testing strategy

### Backend

Unit test:

- health rules
- alert rules
- telemetry normalization
- simulator behavior
- authentication helpers
- service methods

Integration test:

- API endpoints
- database persistence
- telemetry ingestion
- alert lifecycle

### Frontend

Test:

- protected routes
- telemetry state handling
- dashboard rendering
- alert interactions
- replay controls
- responsive behavior

### End-to-end demo test

At minimum:

```text
login
→ select demo drone
→ start normal flight
→ switch to fault scenario
→ observe telemetry change
→ health decreases
→ alert appears
→ recommendation appears
→ open flight
→ replay event
→ create maintenance task
```

---

## 24. Performance requirements

- Avoid rerendering the entire dashboard for every telemetry packet.
- Update only components whose data changed.
- Buffer or throttle visual chart updates where necessary while preserving meaningful telemetry.
- Virtualize large historical datasets if needed.
- Lazy-load heavy application routes.
- Optimize generated image assets for web delivery.
- Avoid shipping unused libraries and oversized images.

---

## 25. Security requirements

- Never commit secrets.
- Validate all incoming API payloads.
- Authenticate protected endpoints.
- Apply authorization checks to drone/flight ownership.
- Sanitize user-provided text displayed in the UI.
- Do not expose internal database errors to users.
- Restrict CORS appropriately outside local development.
- Log operational failures without logging passwords or sensitive tokens.

---

## 26. AI extension boundary

Future AI capabilities must be implemented behind service interfaces rather than mixed into the rule engine.

Possible future interfaces:

```text
AnomalyDetectionService
FaultPredictionService
PredictiveMaintenanceService
IntelligentHealthScoringService
```

The current product may expose these as future capability areas, but the frontend must not claim that a model is running unless a real model/service is connected.

---

## 27. Observability

The system should provide structured logs for:

- application startup
- telemetry connection/disconnection
- simulator start/stop
- alert creation
- critical service failures
- database failures
- authentication failures

A request ID/correlation ID should be used where practical so API errors and backend logs can be connected.

---

## 28. Deployment target

The architecture must remain suitable for:

1. Local development on a laptop.
2. Docker-based demonstration/deployment.
3. Future edge deployment, including Raspberry Pi-class hardware.
4. Future remote connectivity such as LTE.

The original project direction explicitly identifies Raspberry Pi as an edge target and future LTE connectivity as an extension point.

---

## 29. Non-negotiable product behavior

Manus must not:

- replace the backend with static mock JSON only
- build a dashboard that has no live data flow
- fake telemetry with numbers that never change
- claim AI anomaly detection exists before it exists
- create frontend-only alert logic that bypasses the backend architecture
- generate software architecture as decorative screenshots
- restructure the repository without a concrete technical reason
- introduce unnecessary microservices
- turn the product into a generic dark cybersecurity interface

Manus should:

- preserve the repository structure
- use the supplied visual assets
- implement actual routes and protected routes
- keep services modular
- make simulator behavior drive real application state
- make the dashboard respond to backend telemetry
- keep future AI interfaces separate from current rule-based logic

---

## 30. Source alignment

The architecture is based on the project's supplied requirements: telemetry from Pixhawk/ArduPilot using MAVLink, telemetry parsing and storage, REST APIs, live monitoring, cockpit view, component health monitoring, rule-based alerts, flight history and replay, maintenance records, and future AI expansion.

The recommended stack is Python/FastAPI, pymavlink, SQLite/PostgreSQL, React and Docker.
