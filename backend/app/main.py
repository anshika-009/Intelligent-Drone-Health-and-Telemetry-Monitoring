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
    8. Record telemetry into per-user flight sessions (Postgres).

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
import threading
import time
from datetime import datetime, timezone

from fastapi import (
    Depends,
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
    get_current_user,
    get_current_user_ws,
)


# Database

from app.database.session import (
    initialize,
    persist_telemetry,
    resume_or_start_flight,
    start_flight,
    end_flight,
    close_open_flights,
    record_flight_home,
    get_flight_home,
    get_drone_home,
    reset_drone_home,
    list_flights,
    get_flight,
)


# Health intelligence

from app.services.health.engine import (
    analyze_health,
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

maintenance: list[dict] = []

# Which flight (DB row id) is currently open for each signed-in user.
active_flights: dict[str, int] = {}

# Guards start/end so two simultaneous requests can't create two flights.
_flight_lock = threading.Lock()

# Flights whose home position has already been recorded (the DB also
# enforces write-once, this just avoids a DB call on every message).
homes_recorded: set[int] = set()

# Connection string is stored globally so the watchdog can rebuild a
# fresh PipelineRunner (and therefore a fresh socket) without needing
# to re-read the environment each time.
_connection_string: str | None = None

# ---------------------------------------------------------
# Pipeline activation gate
# ---------------------------------------------------------
#
# The MAVLink pipeline must NOT run just because the backend process is
# up. It should only be connected/polling while someone actually has the
# dashboard open AND has it set to "running" (not paused) - that's what
# an entry in `active_flights` represents. Outside of that window the
# transport is fully closed, so no telemetry (good or bad, e.g. the
# (0,0)/simulator-default GPS placeholder emitted right after a
# reconnect) can be produced or persisted.
#
# This does NOT affect reading past flights: `/api/flights` and
# `/api/flights/{id}` read straight from Postgres and never touch the
# pipeline, so historical flight logs stay visible regardless of
# whether the pipeline is currently active.
_pipeline_should_run = False

# Wall-clock bookkeeping for the staleness watchdog. Kept at module
# scope (rather than local to telemetry_polling_loop) so activation/
# deactivation can reset them cleanly.
_last_message_time = time.monotonic()
_next_reconnect_attempt = 0.0


def _activate_pipeline() -> None:
    """Request that the MAVLink transport be turned on. Called when the
    first user's dashboard starts a flight (dashboard open + not
    paused).

    IMPORTANT: this only flips a flag. FastAPI's sync `def` request
    handlers run in a worker thread, separate from the asyncio event
    loop that telemetry_polling_loop() runs on. The actual
    connect()/close() calls on the MAVLink socket must only ever happen
    from telemetry_polling_loop() itself (the loop already owns that
    socket exclusively), so the loop is the one that reacts to this
    flag, not this function."""
    global _pipeline_should_run
    _pipeline_should_run = True


def _deactivate_pipeline() -> None:
    """Request that the MAVLink transport be turned off - see
    _activate_pipeline() for why this only flips a flag."""
    global _pipeline_should_run
    _pipeline_should_run = False


# ---------------------------------------------------------
# Flight recording settings
# ---------------------------------------------------------

# Minimum seconds between two saved snapshots of the same flight.
PERSIST_INTERVAL = 1.0

# Even if nothing changed, save at least this often so the flight
# timeline has no long gaps.
HEARTBEAT = 10.0

# flight_id -> (monotonic time of last save, snapshot that was saved)
last_saved: dict[int, tuple[float, dict]] = {}


def _changed(prev: dict, cur: dict) -> bool:
    """True if anything worth recording changed between two snapshots."""

    def moved(key: str, tolerance: float) -> bool:
        a, b = prev.get(key), cur.get(key)
        if a is None and b is None:
            return False
        if a is None or b is None:
            return True
        return abs(a - b) > tolerance

    return (
        moved("latitude", 1e-6)        # about 0.1 m
        or moved("longitude", 1e-6)
        or moved("altitude", 0.2)
        or moved("battery_percentage", 0.5)
        or moved("signal_strength", 2)
        or moved("health_score", 1)
    )


def _has_valid_position(t: dict) -> bool:
    """A usable GPS position: real coordinates, not the (0, 0) placeholder,
    and the GPS not explicitly reporting 'no fix'."""
    lat, lon = t.get("latitude"), t.get("longitude")
    if lat is None or lon is None:
        return False
    if lat == 0 and lon == 0:
        return False
    if not t.get("gps_fix", True):
        return False
    return True


def _initialize_db_with_retry(attempts: int = 10, delay: float = 2.0) -> None:
    """Postgres may still be starting when the backend boots (docker compose
    only waits for the container to start, not for the DB to accept
    connections), so retry a few times before giving up."""
    for attempt in range(1, attempts + 1):
        try:
            initialize()
            return
        except Exception as error:
            print(
                f"[db] initialize failed (attempt {attempt}/{attempts}): {error}",
                flush=True,
            )
            if attempt == attempts:
                raise
            time.sleep(delay)


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
    global _last_message_time
    global _next_reconnect_attempt

    STALE_TIMEOUT_SECONDS = 5.0
    RECONNECT_COOLDOWN_SECONDS = 3.0

    def force_reconnect(reason: str) -> None:
        global _last_message_time, _next_reconnect_attempt
        print(f"[pipeline] forcing reconnect ({reason})", flush=True)
        try:
            if pipeline_runner:
                pipeline_runner.stop()
        except Exception as stop_error:
            print(f"[pipeline] error while stopping old connection: {stop_error}", flush=True)
        try:
            if pipeline_runner:
                pipeline_runner.start()
                set_pipeline_runner(pipeline_runner)
                print("[pipeline] reconnected to MAVLink source", flush=True)
            _last_message_time = time.monotonic()
        except Exception as start_error:
            print(
                f"[pipeline] reconnect failed, retrying in "
                f"{RECONNECT_COOLDOWN_SECONDS}s: {start_error}",
                flush=True,
            )
        _next_reconnect_attempt = time.monotonic() + RECONNECT_COOLDOWN_SECONDS

    while True:
        try:
            if pipeline_runner:
                now = time.monotonic()

                # Dashboard just opened / resumed from paused (or this is
                # recovering from an unexpected drop while still desired
                # to run): (re)open the transport here, on the loop's own
                # thread, subject to the same cooldown as any other
                # reconnect attempt.
                if (
                    _pipeline_should_run
                    and not pipeline_runner.is_active
                    and now >= _next_reconnect_attempt
                ):
                    try:
                        # start() can block for up to 10s (waiting for the
                        # first heartbeat). Run it in a worker thread so the
                        # whole API does not freeze while it waits.
                        await asyncio.to_thread(pipeline_runner.start)
                        set_pipeline_runner(pipeline_runner)
                        _last_message_time = time.monotonic()
                        print("[pipeline] activated (dashboard running)", flush=True)
                    except Exception as start_error:
                        print(
                            f"[pipeline] activation failed, retrying in "
                            f"{RECONNECT_COOLDOWN_SECONDS}s: {start_error}",
                            flush=True,
                        )
                    _next_reconnect_attempt = time.monotonic() + RECONNECT_COOLDOWN_SECONDS

                # Dashboard paused / closed (no user has an open flight
                # any more): close the transport so nothing more gets
                # produced or persisted until it's reactivated.
                elif not _pipeline_should_run and pipeline_runner.is_active:
                    try:
                        pipeline_runner.stop()
                        print("[pipeline] deactivated (dashboard paused/closed)", flush=True)
                    except Exception as stop_error:
                        print(f"[pipeline] error while stopping connection: {stop_error}", flush=True)

                if _pipeline_should_run and pipeline_runner.is_active:

                    stale = (now - _last_message_time) > STALE_TIMEOUT_SECONDS
                    if stale and now >= _next_reconnect_attempt:
                        # Blocking (stop + start), so keep it off the event loop.
                        await asyncio.to_thread(
                            force_reconnect,
                            f"no data for over {STALE_TIMEOUT_SECONDS}s",
                        )

                if _pipeline_should_run and pipeline_runner.is_active:

                    # Drain queued MAVLink messages so the backend does not
                    # publish an increasingly old packet from the receive queue.
                    processed = pipeline_runner.poll_available()

                    if processed:

                        _last_message_time = time.monotonic()

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

                        # Persist snapshots into every currently-open flight
                        # (rate-limited, and only when something changed).
                        save_time = time.monotonic()
                        for flight_id in list(active_flights.values()):
                            # Record the takeoff ("home") position once per
                            # flight, from the first valid GPS fix. This is
                            # independent of the save rate limit below.
                            if flight_id not in homes_recorded and _has_valid_position(telemetry):
                                try:
                                    record_flight_home(
                                        flight_id,
                                        telemetry["latitude"],
                                        telemetry["longitude"],
                                        telemetry.get("altitude"),
                                    )
                                    homes_recorded.add(flight_id)
                                except Exception as home_error:
                                    print(f"[flight] failed to record home for {flight_id}: {home_error}", flush=True)

                            prev = last_saved.get(flight_id)
                            if prev:
                                saved_at, snapshot = prev
                                if save_time - saved_at < PERSIST_INTERVAL:
                                    continue
                                if (
                                    save_time - saved_at < HEARTBEAT
                                    and not _changed(snapshot, telemetry)
                                ):
                                    continue
                            # Never write a placeholder/no-fix position as if
                            # it were a real point - that's what produces the
                            # "zigzag fan" on the map (straight lines jumping
                            # between the real track and a (0,0) or simulator
                            # default coordinate). Everything else about the
                            # snapshot (battery, health, etc.) is still saved.
                            if _has_valid_position(telemetry):
                                to_save = telemetry
                            else:
                                to_save = dict(telemetry)
                                to_save["latitude"] = None
                                to_save["longitude"] = None

                            try:
                                persist_telemetry(flight_id, to_save)
                                last_saved[flight_id] = (save_time, dict(telemetry))
                            except Exception as db_error:
                                print(
                                    f"[telemetry] failed to persist to flight "
                                    f"{flight_id}: {db_error}",
                                    flush=True,
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

    _initialize_db_with_retry()
    # Flights left open by a previous run can't be resumed (active_flights
    # is in memory), so close them.
    close_open_flights()

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
        f"Telemetry pipeline configured for: {connection_string} "
        f"(will connect once the dashboard opens with telemetry running)",
        flush=True,
    )
    try:
        # Create exactly ONE pipeline runner. IMPORTANT: do NOT call
        # .start() here. Constructing PipelineRunner/MAVLinkSource does
        # not open any socket by itself (.connect() is what does that),
        # so this is safe to do unconditionally at boot. The actual
        # MAVLink connection is opened later, on demand, by
        # _activate_pipeline() - i.e. the first time a user's dashboard
        # starts a flight (dashboard open + telemetry set to running).
        pipeline_runner = PipelineRunner(
            connection_string=connection_string
        )

        # Give the bridge the SAME runner (not yet connected).
        set_pipeline_runner(
            pipeline_runner
        )

        # Start background telemetry processing. It stays idle
        # (see _pipeline_should_run) until a dashboard activates it.
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


# Flights

@app.post('/api/flights/start')
def flight_start(force_new: bool = False, user_id: str = Depends(get_current_user)):
    with _flight_lock:
        if user_id in active_flights and not force_new:
            return {'flight_id': active_flights[user_id], 'status': 'already_active'}
        # If nobody else currently has a flight open, this call is the
        # one that's actually turning the pipeline on (dashboard opened
        # / resumed from paused).
        was_idle = len(active_flights) == 0
        if force_new:
            # User explicitly asked for a brand new flight (not a resume
            # of whatever was paused) - e.g. "Start new flight" after a
            # pause. Skip the resume-window check entirely so a fresh
            # flight row (with no home yet) is always created; its home
            # will be recorded fresh from the next real GPS fix, i.e.
            # wherever the aircraft currently is.
            flight_id = start_flight(user_id, drone_id='DRONE-01', scenario='live_mavlink')
            resumed = False
        else:
            flight_id, resumed = resume_or_start_flight(
                user_id, drone_id='DRONE-01', scenario='live_mavlink'
            )
        active_flights[user_id] = flight_id
        if was_idle:
            _activate_pipeline()
        return {'flight_id': flight_id, 'status': 'resumed' if resumed else 'started'}

@app.post('/api/flights/end')
def flight_end(user_id: str = Depends(get_current_user)):
    with _flight_lock:
        flight_id = active_flights.pop(user_id, None)
        # If that was the last open flight, nobody has the dashboard
        # running any more - shut the pipeline down. Past flights (this
        # one included) stay fully readable from Postgres either way.
        now_idle = len(active_flights) == 0
    if flight_id is None:
        raise HTTPException(404, 'No active flight to end.')
    last_saved.pop(flight_id, None)
    homes_recorded.discard(flight_id)
    end_flight(flight_id)
    if now_idle:
        _deactivate_pipeline()
    return {'flight_id': flight_id, 'status': 'ended'}

@app.get('/api/flights')
def list_flights_endpoint(user_id: str = Depends(get_current_user)):
    return list_flights(user_id)

# Drone home position (permanent, per user, shared by that user's flights)

@app.get('/api/home')
def drone_home(user_id: str = Depends(get_current_user)):
    return {'home': get_drone_home(user_id, 'DRONE-01')}

@app.post('/api/home/reset')
def drone_home_reset(user_id: str = Depends(get_current_user)):
    reset_drone_home(user_id, 'DRONE-01')
    # This user's open flight will re-record its home from the next fix.
    open_flight = active_flights.get(user_id)
    if open_flight is not None:
        homes_recorded.discard(open_flight)
    return {'status': 'reset'}

# NOTE: must stay ABOVE '/api/flights/{flight_id}', otherwise 'active'
# would be parsed as a flight id.
@app.get('/api/flights/active')
def flight_active(user_id: str = Depends(get_current_user)):
    flight_id = active_flights.get(user_id)
    if flight_id is None:
        return {'flight_id': None, 'home': None, 'started_at': None}
    info = get_flight_home(flight_id) or {'home': None, 'started_at': None}
    return {'flight_id': flight_id, **info}

@app.get('/api/flights/{flight_id}')
def flight(flight_id: int, user_id: str = Depends(get_current_user)):
    match = get_flight(flight_id, user_id)
    if not match:
        raise HTTPException(404, 'Flight session not found.')
    return match

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