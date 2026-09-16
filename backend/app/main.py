"""
IDHTM FastAPI Application
-------------------------

Responsibilities:

    1. Start the telemetry pipeline.
    2. Poll telemetry continuously.
    3. Convert VehicleState into backend telemetry.
    4. Run the Health Intelligence Engine.
    5. Store the latest telemetry snapshot.
    6. Serve REST APIs.
    7. Stream the same snapshot through WebSocket.

IMPORTANT:

    The simulator must NOT be advanced from individual REST
    requests.

    There is ONE telemetry producer:

        telemetry_polling_loop()

    All APIs consume latest_telemetry_state.
"""

import asyncio
import os
import sys
import time
from datetime import datetime, timezone

from fastapi import (
    FastAPI,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware


# ---------------------------------------------------------
# Add telemetry pipeline to Python path
# ---------------------------------------------------------

PIPELINE_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "../../telemetry_pipeline",
    )
)

if PIPELINE_ROOT not in sys.path:
    sys.path.insert(0, PIPELINE_ROOT)


# Telemetry pipeline imports

try:

    from src.orchestrator.pipeline_runner import PipelineRunner

    from src.integration.backend_adapter import (
        adapt_to_backend,
    )

    PIPELINE_AVAILABLE = True

except ImportError:

    PipelineRunner = None
    adapt_to_backend = None
    PIPELINE_AVAILABLE = False


# Authentication

from app.core.clerk_auth import (
    get_current_user_ws,
)


# Database

from app.database.session import (
    initialize,
    persist_telemetry,
)


# Health intelligence

from app.services.health.engine import (
    analyze_health,
    component_health,
    explainable_rules,
)


# Telemetry bridge

from app.services.telemetry.pipeline_bridge import (
    set_pipeline_runner,
)


# Schemas

from app.schemas.telemetry import (
    ScenarioRequest,
)


# Application

app = FastAPI(
    title="IDHTM Telemetry API",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global telemetry state

pipeline_runner = None

latest_telemetry_state: dict = {}

latest_health_analysis: dict = {}

flights: list[dict] = []

maintenance: list[dict] = []

# Connection string is stored globally so the watchdog can rebuild a
# fresh PipelineRunner (and therefore a fresh socket) without needing
# to re-read the environment each time.
_connection_string: str | None = None


# Telemetry polling loop

async def telemetry_polling_loop():
    """
    Polls the telemetry pipeline continuously.

    This is the ONLY place where poll_once() is called.

    Therefore:

        REST API     ─┐
        WebSocket    ─┼──> same latest telemetry state
        Dashboard    ─┘

    IMPORTANT - staleness watchdog:

        pymavlink's TCP transport can silently retry a dead connection
        internally (it prints "EOF on TCP socket" and keeps trying to
        reconnect *inside* recv_match) without ever raising a Python
        exception. That means `pipeline_runner.is_active` can stay
        True forever even though no new messages are actually
        arriving, and the dashboard would silently keep showing the
        last snapshot from before the disconnect.

        To defend against that, we track the wall-clock time of the
        last successfully processed message. If too much time passes
        without one, we force a full reconnect (stop + start, which
        throws away the old, possibly wedged socket and opens a brand
        new one) - regardless of whether an exception was ever raised.
    """

    global latest_telemetry_state
    global latest_health_analysis
    global pipeline_runner

    STALE_TIMEOUT_SECONDS = 5.0
    RECONNECT_COOLDOWN_SECONDS = 3.0

    last_message_time = time.monotonic()
    next_reconnect_attempt = 0.0

    def force_reconnect(reason: str) -> None:
        nonlocal last_message_time, next_reconnect_attempt
        print(f"[pipeline] forcing reconnect ({reason})", flush=True)
        try:
            if pipeline_runner:
                pipeline_runner.stop()
        except Exception as stop_error:
            print(f"[pipeline] error while stopping old connection: {stop_error}", flush=True)
        try:
            pipeline_runner.start()
            set_pipeline_runner(pipeline_runner)
            print("[pipeline] reconnected to MAVLink source", flush=True)
            last_message_time = time.monotonic()
        except Exception as start_error:
            print(
                f"[pipeline] reconnect failed, retrying in "
                f"{RECONNECT_COOLDOWN_SECONDS}s: {start_error}",
                flush=True,
            )
        next_reconnect_attempt = time.monotonic() + RECONNECT_COOLDOWN_SECONDS

    while True:

        try:

            if pipeline_runner:

                now = time.monotonic()

                transport_down = not pipeline_runner.is_active
                stale = (now - last_message_time) > STALE_TIMEOUT_SECONDS

                if (transport_down or stale) and now >= next_reconnect_attempt:
                    force_reconnect(
                        "transport reported inactive"
                        if transport_down
                        else f"no data for over {STALE_TIMEOUT_SECONDS}s"
                    )

                if pipeline_runner.is_active:

                    # Drain queued MAVLink messages so the backend does not
                    # publish an increasingly old packet from the receive queue.
                    processed = pipeline_runner.poll_available()

                    if processed:

                        last_message_time = time.monotonic()

                        # Get aggregated canonical state.
                        state = pipeline_runner.get_state()

                        # Convert canonical state to backend format.
                        telemetry = adapt_to_backend(state)

                        # Run your health intelligence.
                        health = analyze_health(
                            telemetry
                        )

                        # Add derived health score.
                        telemetry["health_score"] = (
                            health["score"]
                        )

                        # Store the SAME snapshot used by
                        # REST and WebSocket.
                        latest_telemetry_state = telemetry

                        latest_health_analysis = health

                        # Persist one snapshot.
                        persist_telemetry(
                            telemetry,
                            "live_mavlink",
                        )

        except Exception as error:

            # Do not kill the telemetry loop if one packet
            # causes an unexpected processing error.
            print(
                f"Telemetry processing error: {error}",
                flush=True,
            )

        # 50 Hz polling loop.
        #
        # The aggregator itself handles message rates
        # and category freshness.
        await asyncio.sleep(0.02)

# Startup
@app.on_event("startup")
def startup() -> None:

    global pipeline_runner
    global _connection_string

    initialize()

    if not PIPELINE_AVAILABLE:

        print(
            "Telemetry pipeline is unavailable.",
            flush=True,
        )

        return
    
    connection_string = os.environ.get(
        "MAVLINK_URL",
        "udp:127.0.0.1:14550",
    )
    _connection_string = connection_string

    print(
        f"Starting IDHTM telemetry pipeline: "
        f"{connection_string}",
        flush=True,
    )
    try:
        # Create exactly ONE pipeline runner.
        pipeline_runner = PipelineRunner(
            connection_string=connection_string
        )

        pipeline_runner.start()

        # Give the bridge the SAME runner.
        set_pipeline_runner(
            pipeline_runner
        )

        # Start background telemetry processing.
        asyncio.create_task(
            telemetry_polling_loop()
        )
    except Exception as error:
        print(
            f"[startup] MAVLink pipeline unavailable, falling back to simulator: {error}",
            flush=True,
        )
        pipeline_runner = None
# Healthcheck

@app.get("/api/healthcheck")
def healthcheck():

    return {
        "status": "ok",
        "service": "idhtm-api",
        "time": datetime.now(
            timezone.utc
        ).isoformat(),
    }


# Drones

@app.get("/api/drones")
def drones():

    telemetry = latest_telemetry_state

    return [
        {
            "id": telemetry.get(
                "drone_id",
                "DRONE-01",
            ),
            "name": "DRONE-01",
            "model": "Industrial Survey Mk II",
            "status": (
                "connected"
                if pipeline_runner
                and pipeline_runner.is_active
                else "disconnected"
            ),
            "health": telemetry.get(
                "health_score"
            ),
        }
    ]


# Latest telemetry

@app.get("/api/telemetry/latest")
def latest():

    if not latest_telemetry_state:

        raise HTTPException(
            status_code=503,
            detail="Telemetry is not available yet.",
        )

    return latest_telemetry_state


# Pipeline telemetry

@app.get("/api/telemetry/pipeline/latest")
def pipeline_latest():

    if not latest_telemetry_state:

        raise HTTPException(
            status_code=503,
            detail="Telemetry pipeline has not produced data yet.",
        )

    return latest_telemetry_state


# Health

@app.get("/api/health")
def health():

    if not latest_telemetry_state:

        raise HTTPException(
            status_code=503,
            detail="Health data is not available yet.",
        )

    return latest_health_analysis


# Alerts

@app.get("/api/alerts")
def alerts():

    if not latest_telemetry_state:

        return []

    rules = explainable_rules(
        latest_telemetry_state
    )

    return [
        {
            **rule,
            "id": (
                f"RULE-{rule['id'].upper()}"
            ),
            "timestamp": latest_telemetry_state[
                "timestamp"
            ],
            "acknowledged": False,
        }
        for rule in rules
    ]


# Alert acknowledgement

@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge(alert_id: str):

    return {
        "id": alert_id,
        "acknowledged": True,
    }


# Scenario endpoint

@app.post("/api/telemetry/scenario")
def set_scenario(request: ScenarioRequest):

    # IMPORTANT:
    #
    # The real telemetry source is now MAVLink/SITL.
    #
    # Scenario injection should be implemented as a separate
    # fault-injection layer rather than changing the MAVLink
    # receiver.
    #
    # For now we acknowledge the requested scenario so the
    # frontend remains compatible.

    return {
        "scenario": request.scenario,
        "status": "accepted",
        "message": (
            "Scenario selection is ready for the "
            "fault-injection layer."
        ),
    }


# WebSocket telemetry

@app.websocket("/ws/telemetry")
async def telemetry_socket(
    websocket: WebSocket,
):

    user_id = await get_current_user_ws(
        websocket
    )

    if user_id is None:
        return

    await websocket.accept()

    try:

        while True:

            # IMPORTANT:
            #
            # Never call simulator.next() here.
            #
            # The WebSocket sends the same state produced
            # by telemetry_polling_loop().

            if latest_telemetry_state:

                await websocket.send_json(
                    {
                        "telemetry": (
                            latest_telemetry_state
                        ),
                        "health": (
                            latest_health_analysis
                        ),
                        "alerts": (
                            latest_health_analysis.get(
                                "rules",
                                [],
                            )
                        ),
                        "recommendations": (
                            latest_health_analysis.get(
                                "recommendations",
                                [],
                            )
                        ),
                        "mavlink_connected": (
                            pipeline_runner is not None
                            and pipeline_runner.is_active
                        ),
                    }
                )

            await asyncio.sleep(1)

    except (
        WebSocketDisconnect,
        asyncio.CancelledError,
    ):

        return


# Drone location WebSocket

@app.websocket("/ws/drone-location")
async def drone_location_socket(
    websocket: WebSocket,
):

    user_id = await get_current_user_ws(
        websocket
    )

    if user_id is None:
        return

    await websocket.accept()

    try:

        while True:

            telemetry = latest_telemetry_state

            if telemetry:

                # Only send location if it is available.
                if (
                    telemetry.get("latitude")
                    is not None
                    and
                    telemetry.get("longitude")
                    is not None
                ):

                    await websocket.send_json(
                        {
                            "drone_id": telemetry.get(
                                "drone_id",
                                "DRONE-01",
                            ),
                            "flight_id": telemetry.get(
                                "flight_id",
                                "FLT-LIVE-01",
                            ),
                            "timestamp": telemetry[
                                "timestamp"
                            ],
                            "latitude": telemetry[
                                "latitude"
                            ],
                            "longitude": telemetry[
                                "longitude"
                            ],
                            "altitude": telemetry.get(
                                "altitude"
                            ),
                            "heading": telemetry.get(
                                "heading"
                            ),
                        }
                    )

            await asyncio.sleep(1)

    except (
        WebSocketDisconnect,
        asyncio.CancelledError,
    ):

        return

@app.get('/api/flights')
def list_flights():
    return flights

@app.get('/api/flights/{flight_id}')
def flight(flight_id: str):
    match = next((item for item in flights if item['id'] == flight_id), None)
    if not match:
        raise HTTPException(404, 'Flight session not found.')
    return {**match, 'telemetry': [], 'events': []}

@app.get('/api/maintenance')
def list_maintenance():
    return maintenance

@app.post('/api/maintenance')
def create_maintenance(payload: dict):
    item = {
        'id': f"MNT-{len(maintenance) + 1:03d}",
        'created_at': datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    maintenance.append(item)
    return item

@app.patch('/api/maintenance/{item_id}')
def update_maintenance(item_id: str, payload: dict):
    for item in maintenance:
        if item['id'] == item_id:
            item.update(payload)
            return item
    raise HTTPException(404, 'Maintenance record not found.')

@app.get('/api/reports')
def reports():
    return [
        {
            'id': 'RPT-FLIGHT-01',
            'type': 'Flight summary',
            'title': 'Flight summary / FLT-2026-0821-07',
            'status': 'ready',
        },
        {
            'id': 'RPT-HEALTH-01',
            'type': 'Health summary',
            'title': 'Health summary / DRONE-01',
            'status': 'ready',
        },
    ]

@app.get('/api/connections')
def connections():
    pipeline_connected = (
        pipeline_runner is not None
        and pipeline_runner.is_active
    )

    return [
        {
            'source': 'MAVLink pipeline',
            'state': 'connected' if pipeline_connected else 'disconnected',
            'packets_per_second': None,
            'latency_ms': None,
            'message_count': None,
            'last_update': datetime.now(timezone.utc).isoformat(),
        },
        {
            'source': 'Pixhawk / MAVLink',
            'state': 'available',
            'packets_per_second': 0,
            'latency_ms': None,
            'message_count': 0,
            'last_update': None,
        },
        {
            'source': 'ArduPilot SITL',
            'state': 'available',
            'packets_per_second': 0,
            'latency_ms': None,
            'message_count': 0,
            'last_update': None,
        },
    ]