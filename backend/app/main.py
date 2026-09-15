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


# Telemetry polling loop

async def telemetry_polling_loop():
    """
    Polls the telemetry pipeline continuously.

    This is the ONLY place where poll_once() is called.

    Therefore:

        REST API     ─┐
        WebSocket    ─┼──> same latest telemetry state
        Dashboard    ─┘
    """

    global latest_telemetry_state
    global latest_health_analysis

    while True:

        try:

            if pipeline_runner:

                # Drain queued MAVLink messages so the backend does not
                # publish an increasingly old packet from the receive queue.
                processed = pipeline_runner.poll_available()

                if processed:

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

    initialize()

    if not PIPELINE_AVAILABLE:

        print(
            "Telemetry pipeline is unavailable.",
            flush=True,
        )

        return

    # Read the MAVLink connection from environment.
    #
    # Example:
    #
    # MAVLINK_URL=udp:127.0.0.1:14551
    #
    connection_string = os.environ.get(
        "MAVLINK_URL",
        "udp:127.0.0.1:14550",
    )

    print(
        f"Starting IDHTM telemetry pipeline: "
        f"{connection_string}",
        flush=True,
    )

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

# import asyncio

# import sys
# import os
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../telemetry_pipeline')))
# try:
#     from src.orchestrator.pipeline_runner import PipelineRunner
#     from src.integration.backend_adapter import adapt_to_backend
#     PIPELINE_AVAILABLE = True
# except ImportError:
#     PIPELINE_AVAILABLE = False
# from app.services.health.engine import calculate_health

# from datetime import datetime, timezone
# from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
# from fastapi.middleware.cors import CORSMiddleware

# from app.core.clerk_auth import get_current_user, get_current_user_ws
# from app.database.session import initialize, persist_telemetry
# from app.schemas.telemetry import ScenarioRequest
# from app.services.health.engine import explainable_rules, component_health
# from app.services.telemetry.simulator import Simulator, SCENARIOS
# from app.services.rule_engine import IDHTMRuleEngine
# from app.services.telemetry.pipeline_bridge import get_latest_telemetry

# app = FastAPI(title='IDHTM Telemetry API', version='1.0.0')
# physics_engine = IDHTMRuleEngine()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=['*'],
#     allow_credentials=True,
#     allow_methods=['*'],
#     allow_headers=['*'],
# )


# pipeline_runner = None
# latest_telemetry_state = None

# async def telemetry_polling_loop():
#     global latest_telemetry_state
#     while True:
#         if pipeline_runner and pipeline_runner.poll_once():
#             state = pipeline_runner.get_state()
#             legacy_dict = adapt_to_backend(state)
#             legacy_dict['health_score'] = calculate_health(legacy_dict)
#             latest_telemetry_state = legacy_dict
#         await asyncio.sleep(0.02)

# simulator = Simulator()

# maintenance = [
#     {
#         'id': 'MNT-001',
#         'component': 'Motor 2',
#         'issue': 'Potential bearing wear',
#         'recommendation': 'Inspect motor bearing before next extended flight.',
#         'severity': 'Medium',
#         'status': 'Pending',
#         'created_at': '2026-08-21T14:50:00Z',
#     }
# ]

# flights = [
#     {
#         'id': 'FLT-2026-0821-07',
#         'date': '21 Aug 2026 · 14:32',
#         'duration': '18m 42s',
#         'health': 92,
#         'alerts': 2,
#         'summary': 'Stable survey flight. Minor signal fluctuation on descent.',
#     },
#     {
#         'id': 'FLT-2026-0820-03',
#         'date': '20 Aug 2026 · 09:18',
#         'duration': '26m 11s',
#         'health': 88,
#         'alerts': 4,
#         'summary': 'Extended inspection flight with rising motor vibration.',
#     },
#     {
#         'id': 'FLT-2026-0818-11',
#         'date': '18 Aug 2026 · 16:05',
#         'duration': '12m 28s',
#         'health': 97,
#         'alerts': 0,
#         'summary': 'Nominal mapping flight across the north sector.',
#     },
# ]

# @app.on_event('startup')
# def startup() -> None:
#     initialize()

#     global pipeline_runner
#     if PIPELINE_AVAILABLE:
#         pipeline_runner = PipelineRunner(connection_string=os.environ.get('MAVLINK_URL', 'udp:127.0.0.1:14550'))
#         pipeline_runner.start()
#         asyncio.create_task(telemetry_polling_loop())


# @app.get('/api/healthcheck')
# def healthcheck():
#     return {
#         'status': 'ok',
#         'service': 'idhtm-api',
#         'time': datetime.now(timezone.utc).isoformat(),
#     }

# @app.get('/api/drones')
# def drones(user_id: str = Depends(get_current_user)):
#     return [
#         {
#             'id': 'DRONE-01',
#             'name': 'DRONE-01',
#             'model': 'Industrial Survey Mk II',
#             'status': 'simulator_active',
#             'health': simulator.next()['health_score'],
#         }
#     ]

# @app.get('/api/telemetry/scenarios')
# def scenarios(user_id: str = Depends(get_current_user)):
#     return [{'id': key, **value} for key, value in SCENARIOS.items()]

# @app.post('/api/telemetry/scenario')
# def set_scenario(request: ScenarioRequest, user_id: str = Depends(get_current_user)):
#     try:
#         simulator.set_scenario(request.scenario)
#     except ValueError as error:
#         raise HTTPException(422, str(error))
#     return {'scenario': simulator.scenario, 'status': 'active'}

# @app.get('/api/telemetry/latest')
# def latest(user_id: str = Depends(get_current_user)):
#     event = latest_telemetry_state.copy() if latest_telemetry_state else simulator.next()
#     persist_telemetry(event, simulator.scenario)
#     return event
# @app.get('/api/telemetry/pipeline/latest')
# def pipeline_latest(user_id: str = Depends(get_current_user)):
#     event = get_latest_telemetry()
#     return event


# @app.get('/api/health')
# def health(user_id: str = Depends(get_current_user)):
#     event = latest_telemetry_state.copy() if latest_telemetry_state else simulator.next()
#     return {
#         'scenario': simulator.scenario,
#         'score': event['health_score'],
#         'components': component_health(event),
#         'rules': explainable_rules(event),
#     }

# @app.get('/api/alerts')
# def alerts(user_id: str = Depends(get_current_user)):
#     event = latest_telemetry_state.copy() if latest_telemetry_state else simulator.next()
#     base_alerts = [
#         {
#             **rule,
#             'id': f"RULE-{rule['id'].upper()}",
#             'timestamp': event['timestamp'],
#             'acknowledged': False,
#         }
#         for rule in explainable_rules(event)
#     ]

#     # Injecting AI Rule Engine Logic for REST API
#     voltage = event.get('voltage', 11.2)
#     battery_eval = physics_engine.evaluate_battery_state(voltage)
#     if battery_eval['status'] not in ["NORMAL", "STABLE"]:
#         base_alerts.append({
#             'id': f"RULE-BATT-{battery_eval['status']}",
#             'message': f"Battery {battery_eval['status']}: {battery_eval['action']}",
#             'severity': 'critical' if battery_eval['status'] in ['CRITICAL', 'EMERGENCY'] else 'warning',
#             'timestamp': event['timestamp'],
#             'acknowledged': False,
#         })

#     return base_alerts

# @app.post('/api/alerts/{alert_id}/acknowledge')
# def acknowledge(alert_id: str, user_id: str = Depends(get_current_user)):
#     return {'id': alert_id, 'acknowledged': True}

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

# @app.websocket('/ws/telemetry')
# async def telemetry_socket(websocket: WebSocket):
#     user_id = await get_current_user_ws(websocket)
#     if user_id is None:
#         return
#     await websocket.accept()
#     try:
#         while True:
#             event = latest_telemetry_state.copy() if latest_telemetry_state else simulator.next()
#             persist_telemetry(event, simulator.scenario)

#             # --- AI RULE ENGINE INTEGRATION START ---
#             dynamic_alerts = [
#                 {
#                     **rule,
#                     'id': f"RULE-{rule['id'].upper()}",
#                     'timestamp': event['timestamp'],
#                     'acknowledged': False,
#                 }
#                 for rule in explainable_rules(event)
#             ]

#             # 1. Battery Health Processing
#             voltage = event.get('voltage', 11.2) # Defaults to safe voltage if key is missing
#             battery_eval = physics_engine.evaluate_battery_state(voltage)

#             if battery_eval['status'] not in ["NORMAL", "STABLE"]:
#                 dynamic_alerts.append({
#                     'id': f"RULE-BATT-{battery_eval['status']}",
#                     'message': f"Battery {battery_eval['status']}: {battery_eval['action']}",
#                     'severity': 'critical' if battery_eval['status'] in ['CRITICAL', 'EMERGENCY'] else 'warning',
#                     'timestamp': event['timestamp'],
#                     'acknowledged': False,
#                 })

#             # 2. Motor Health Processing
#             ax = event.get('ax', 0.0)
#             ay = event.get('ay', 0.0)
#             az = event.get('az', 0.0)
#             motor_eval = physics_engine.evaluate_motor_health(ax, ay, az)

#             if motor_eval['vibration_alert']:
#                 dynamic_alerts.append({
#                     'id': "RULE-MOTOR-VIBE",
#                     'message': motor_eval['risk'],
#                     'severity': 'critical',
#                     'timestamp': event['timestamp'],
#                     'acknowledged': False,
#                 })
#             # --- AI RULE ENGINE INTEGRATION END ---

#             await websocket.send_json(
#                 {
#                     'scenario': simulator.scenario,
#                     'telemetry': event,
#                     'alerts': dynamic_alerts,
#                 }
#             )
#             await asyncio.sleep(1)
#     except (WebSocketDisconnect, asyncio.CancelledError):
#         return

# @app.websocket('/ws/drone-location')
# async def drone_location_socket(websocket: WebSocket):
#     user_id = await get_current_user_ws(websocket)
#     if user_id is None:
#         return
#     await websocket.accept()
#     try:
#         while True:
#             event = latest_telemetry_state.copy() if latest_telemetry_state else simulator.next()
#             await websocket.send_json(
#                 {
#                     'drone_id': 'DRONE-01',
#                     'flight_id': 'FLT-LIVE-01',
#                     'timestamp': event['timestamp'],
#                     'latitude': event['latitude'],
#                     'longitude': event['longitude'],
#                     'altitude': event['altitude'],
#                     'heading': event['heading'],
#                 }
#             )
#             await asyncio.sleep(1)
#     except (WebSocketDisconnect, asyncio.CancelledError):
#         return
