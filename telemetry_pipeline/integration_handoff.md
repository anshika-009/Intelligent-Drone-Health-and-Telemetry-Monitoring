# Telemetry Pipeline — Backend Integration Handoff Specification

## 1. Architectural Boundary

The `telemetry_pipeline` is strictly the telemetry and data-ingestion layer of the architecture.

**It OWNS:**
* MAVLink transport ingestion (UDP/Serial via `mavutil`).
* MAVLink binary parsing and field extraction.
* Normalization to standard SI units (degrees, meters, m/s², volts).
* Telemetry freshness tracking and TTL enforcement (stale values accurately become `None`).
* Field aggregation into a continuous, unified state representation.
* Generation of the canonical `VehicleState` object.
* Pipeline lifecycle and polling mechanics (`start()`, `poll_once()`, `stop()`).

**It DOES NOT OWN:**
* Drone health calculations or business scoring logic.
* Database persistence (ORM mapping, querying, inserts).
* API routes, FastAPI context, or WebSocket broadcast management.
* Domain-specific business logic or alerting.

## 2. Integration Seam — BackendAdapter

The seam between the canonical pipeline and the legacy backend is isolated within the BackendAdapter.

* **Module:** `src.integration.backend_adapter`
* **Function Signature:** `def adapt_to_backend(state: VehicleState) -> Dict[str, Any]`
* **Input Type:** Canonical `VehicleState` model.
* **Output Structure:** Flat standard Python `dict`.
* **Output Fields:** `drone_id`, `flight_id`, `timestamp`, `latitude`, `longitude`, `altitude`, `ground_speed`, `airspeed`, `vertical_speed`, `heading`, `battery_percentage`, `battery_voltage`, `voltage`, `temperature`, `signal_strength`, `gps_fix`, `gps_satellites`, `flight_mode`, `vibration`, `motor_outputs`, `estimated_remaining_flight_time`.
* **Transformations & Coercions:** Fallback logic forces `None` values into raw numbers (`0.0`) and booleans (`False`) to prevent breaking the strict legacy schema. 

## 3. Voltage Compatibility

Both `battery_voltage` (canonical standard) and `voltage` (legacy alias) are emitted identically by `adapt_to_backend`.
The legacy backend AI Engine can continue expecting `voltage` without disruption, while modern modules can safely target `battery_voltage`.

## 4. Stale Data and None Semantics — CRITICAL

**Canonical Behavior:** 
The internal pipeline tracks independent TTLs (Time-To-Live) per category (e.g. IMU vs GPS). When a subset of MAVLink messages stops arriving, those specific stale fields gracefully revert to `None` in the `VehicleState` object. `None` correctly implies "unknown" or "stale".

**Backend Adapter Coercion [CRITICAL WARNING]:**
The current `BackendAdapter` forcefully coerces `None` values to physical zero (`0.0`) and booleans to `False`. 
**Affected fields:** All numerical (coordinates, speeds, battery, temperature, signal strength) and boolean (`gps_fix`) fields.

**Impact:** Converting unknown telemetry into `0.0` will likely trigger catastrophic false alarms or misleading database state (e.g. suddenly displaying the drone at 0° Lat, 0° Lon, or 0% battery). The backend team must prepare their database layers to accept `None`/`NULL` and remove these unsafe `0.0` fallbacks from the adapter as soon as their schema permits.

## 5. Synthetic / Placeholder Fields

The `BackendAdapter` currently hardcodes the following placeholders to satisfy legacy endpoints, because they are not genuinely measured or computed from the ingested MAVLink frames:

* `flight_mode`: `"UNKNOWN"` (str)
* `vibration`: `0.0` (float)
* `motor_outputs`: `[0, 0, 0, 0]` (list of int)
* `estimated_remaining_flight_time`: `20.0` (float)

These values are completely synthetic. Do not use them for flight safety assumptions.

## 6. Health Score Ownership — CRITICAL

**Health scoring is completely outside the telemetry pipeline's responsibility.**
The `BackendAdapter` does NOT emit a `health_score` placeholder or default value. `health_score` is deliberately omitted from the output dict. The backend/physics engine must own and inject its own health calculations over the data before publishing it via WebSockets or databases. The adapter must not be interpreted as a health-analysis engine.

## 7. Runtime / Transport Integration Contract

The integration facade is the `PipelineRunner`.

* **Constructor:** `PipelineRunner(connection_string: Optional[str] = None)`
* **UDP Endpoint:** If no connection string is explicitly provided, it strictly defaults to `os.environ.get('MAVLINK_URL', 'udp:host.docker.internal:14550')` (distinguished from test ports like `14555`).
* **`start()`:** Idempotently initializes the network transport.
* **`poll_once()`:** Non-blocking mechanism that fetches at most one message, attempts to parse and normalize it, and updates the aggregator if valid. Returns `True` if aggregated, `False` otherwise. Does NOT block.
* **`get_state()`:** Synchronously produces the canonical `VehicleState` snapshot based on the latest poll.
* **`stop()`:** Idempotently releases network sockets.
* **Lifecycle Ownership:** The backend application is entirely responsible for spawning a background task, calling `start()`, executing the `poll_once()` loop, and gracefully calling `stop()` upon shutdown.

## 8. Backend Integration Sequence

To safely hook up the pipeline:

```python
from src.orchestrator.pipeline_runner import PipelineRunner
from src.integration.backend_adapter import adapt_to_backend

# 1. Start PipelineRunner
runner = PipelineRunner(connection_string="udp:0.0.0.0:14550")
runner.start()

# 2. Run polling loop in background context
while system_running:
    if runner.poll_once():
        # 3. Retrieve canonical VehicleState
        state = runner.get_state()
        
        # 4. Pass VehicleState through BackendAdapter
        legacy_dict = adapt_to_backend(state)
        
        # 5. Apply backend-owned health/business logic
        legacy_dict['health_score'] = calculate_health(legacy_dict)
        
        # 6. Persist/API-publish
        database.save(legacy_dict)
        websocket.broadcast(legacy_dict)

# 7. Clean Shutdown
runner.stop()
```

## 9. Migration From Legacy Simulator

**CURRENT ARCHITECTURE:**
MAVLink/Simulator → `legacy simulator.next()` → legacy backend processing

**TARGET ARCHITECTURE:**
MAVLink producer → `PipelineRunner` (ingest/parse/normalize/aggregate) → `VehicleState` → `adapt_to_backend()` → Backend health/business logic → Database/API/WebSocket

**Migration Strategy:**
Do not aggressively delete `simulator.py` yet. Integrate the new `PipelineRunner` + `BackendAdapter` loop alongside the old loop. Once the API endpoints prove they can consume the legacy dict format produced by `adapt_to_backend`, you may safely disable and retire the legacy simulator.

## 10. Integration Risks / Required Actions

| Risk | Current Behavior | Impact | Required Backend Action | Priority |
| :--- | :--- | :--- | :--- | :--- |
| `None` coercion to 0.0 | Adapter forces `None` fields to `0.0/False`. | Triggers false alarms when telemetry drops. | Update downstream schemas to accept `NULL`/`None`, then remove adapter f_fallback coercions. | CRITICAL |
| Health score ownership | Omitted from adapter payload completely. | App crashes if it blindly expects `health_score` directly from telemetry ingest. | Inject backend-owned health logic immediately after adapter mapping. | HIGH |
| UDP Endpoint configuration | Defaults to Docker internal networking (`host.docker.internal:14550`). | May fail to bind on bare-metal deployments without env overrides. | Inject proper `MAVLINK_URL` via environment variables. | MED |
| Synthetic placeholder fields | `flight_mode` / `motor_outputs` are hardcoded mocks. | UI will display fake data. | Evaluate whether to omit placeholders or wire them to real domain calculators. | MED |

## 11. Frozen Pipeline Validation Evidence
The pipeline has definitively passed isolated testing up to real-world UDP socket interactions.

* Total Tests: 137
* Passed: 137
* Failed: 0
* Errors: 0
* Skipped: 0
* **6D.5A** (Failure Path / Lifecycle): PASS
* **6D.5B** (Real MAVLink byte conversion): PASS
* **6D.5C** (Live UDP validation): PASS (Confirmed using a genuine `pymavlink` UDP producer over actual sockets; native ArduPilot/PX4 SITL binaries were unavailable).

## 12. Integration Acceptance Criteria

The legacy simulator must NOT be removed until the following criteria are verified in the backend environment:
1. `PipelineRunner` starts and binds cleanly to the real production UDP port.
2. The legacy backend receives the `VehicleState` via `adapt_to_backend` without schema rejections.
3. Health calculations operate flawlessly on the mapped output.
4. Downstream database/API behavior is proven stable.
5. Unknown telemetry behaves cleanly (false zero coercions are removed).
6. No duplicate or overlapping MAVLink consumers exist in the backend context.
7. Clean socket shutdown occurs during backend application teardown.
