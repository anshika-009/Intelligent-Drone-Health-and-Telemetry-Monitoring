import asyncio
import secrets
import logging
import traceback
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.core.security import hash_password, verify_password
from app.database.session import initialize, persist_telemetry
from app.schemas.telemetry import Credentials, ScenarioRequest
from app.services.health.engine import explainable_rules, component_health
from app.services.telemetry.simulator import Simulator, SCENARIOS

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt = '%H:%M:%S',
)

logger = logging.getLogger('idhtm.tick_loop')

app = FastAPI(title='IDHTM Telemetry API', version='1.0.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

simulator = Simulator()
# shared state holder 
latest_event: dict = {}
tick_loop_status = {
    'healthy': True,
    'last_tick_at': None,
    'last_error': None,
    'error_count': 0,
}
users = {
    'operator@idhtm.dev': {
        'name': 'Demo Operator',
        'password': hash_password('demo-flight'),
    }
}
tokens: dict[str, str] = {}

maintenance = [
    {
        'id': 'MNT-001',
        'component': 'Motor 2',
        'issue': 'Potential bearing wear',
        'recommendation': 'Inspect motor bearing before next extended flight.',
        'severity': 'Medium',
        'status': 'Pending',
        'created_at': '2026-08-21T14:50:00Z',
    }
]

flights = [
    {
        'id': 'FLT-2026-0821-07',
        'date': '21 Aug 2026 · 14:32',
        'duration': '18m 42s',
        'health': 92,
        'alerts': 2,
        'summary': 'Stable survey flight. Minor signal fluctuation on descent.',
    },
    {
        'id': 'FLT-2026-0820-03',
        'date': '20 Aug 2026 · 09:18',
        'duration': '26m 11s',
        'health': 88,
        'alerts': 4,
        'summary': 'Extended inspection flight with rising motor vibration.',
    },
    {
        'id': 'FLT-2026-0818-11',
        'date': '18 Aug 2026 · 16:05',
        'duration': '12m 28s',
        'health': 97,
        'alerts': 0,
        'summary': 'Nominal mapping flight across the north sector.',
    },
]

#startup handler seeds the current state and starts the tick loop
@app.on_event('startup')
async def startup() -> None:
    initialize()
    global latest_event
    latest_event = simulator.next()
    asyncio.create_task(_tick_loop())

async def _tick_loop() -> None:
    global latest_event
    while True:
        await asyncio.sleep(1)

        try:
            latest_event = simulator.next()
            persist_telemetry(latest_event, simulator.scenario)
            tick_loop_status['healthy'] = True
            tick_loop_status['last_tick_at'] = datetime.now(timezone.utc).isoformat()

        except Exception as error:
            tick_loop_status['healthy'] = False
            tick_loop_status['last_error'] = str(error)
            tick_loop_status['error_count'] += 1

            logger.error(
                "Tick failed on scenario '%s' (tick #%s): %s\n%s",
                simulator.scenario,
                simulator.tick,
                error,
                traceback.format_exc(),
            )


@app.get('/api/system/status')
def system_status():
    return {
        'tick_loop': tick_loop_status,
        'scenario': simulator.scenario,
        'server_time': datetime.now(timezone.utc).isoformat(),
    }


@app.get('/api/healthcheck')
def healthcheck():
    return {
        'status': 'ok',
        'service': 'idhtm-api',
        'time': datetime.now(timezone.utc).isoformat(),
    }


@app.post('/api/auth/register')
def register(credentials: Credentials):
    if credentials.email in users:
        raise HTTPException(409, 'An operator with this email already exists.')
    if len(credentials.password) < 6:
        raise HTTPException(422, 'Password must be at least 6 characters.')

    users[credentials.email] = {
        'name': credentials.name or 'Flight Operator',
        'password': hash_password(credentials.password),
    }
    token = secrets.token_urlsafe(24)
    tokens[token] = credentials.email
    return {
        'token': token,
        'user': {
            'email': credentials.email,
            'name': users[credentials.email]['name'],
        },
    }


@app.post('/api/auth/login')
def login(credentials: Credentials):
    user = users.get(credentials.email)
    if not user or not verify_password(credentials.password, user['password']):
        raise HTTPException(401, 'Invalid operator credentials.')

    token = secrets.token_urlsafe(24)
    tokens[token] = credentials.email
    return {
        'token': token,
        'user': {
            'email': credentials.email,
            'name': user['name'],
        },
    }


@app.post('/api/auth/logout')
def logout():
    return {'status': 'signed_out'}


@app.get('/api/drones')
def drones():
    return [
        {
            'id': 'DRONE-01',
            'name': 'DRONE-01',
            'model': 'Industrial Survey Mk II',
            'status': 'simulator_active',
            'health': latest_event['health_score'],
        }
    ]


@app.get('/api/telemetry/scenarios')
def scenarios():
    return [{'id': key, **value} for key, value in SCENARIOS.items()]

#lags for about a second before updating
@app.post('/api/telemetry/scenario')
def set_scenario(request: ScenarioRequest):
    try:
        simulator.set_scenario(request.scenario)
    except ValueError as error:
        raise HTTPException(422, str(error))
    return {'scenario': simulator.scenario, 'status': 'active'}


@app.get('/api/telemetry/latest')
def latest():
    return latest_event


@app.get('/api/health')
def health():
    event = latest_event
    return {
        'scenario': simulator.scenario,
        'score': event['health_score'],
        'components': component_health(event),
        'rules': explainable_rules(event),
    }


@app.get('/api/alerts')
def alerts():
    event = latest_event
    return [
        {
            **rule,
            'id': f"RULE-{rule['id'].upper()}",
            'timestamp': event['timestamp'],
            'acknowledged': False,
        }
        for rule in explainable_rules(event)
    ]


@app.post('/api/alerts/{alert_id}/acknowledge')
def acknowledge(alert_id: str):
    return {'id': alert_id, 'acknowledged': True}


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
    return [
        {
            'source': 'Simulator',
            'state': 'connected',
            'packets_per_second': 1,
            'latency_ms': 18,
            'message_count': simulator.tick,
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


@app.websocket('/ws/telemetry')
async def telemetry_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            event = latest_event
            await websocket.send_json(
                {
                    'scenario': simulator.scenario,
                    'telemetry': event,
                    'alerts': [
                        {
                            **rule,
                            'id': f"RULE-{rule['id'].upper()}",
                            'timestamp': event['timestamp'],
                            'acknowledged': False,
                        }
                        for rule in explainable_rules(event)
                    ],
                    'system' : tick_loop_status
                }
            )
            await asyncio.sleep(1)
    except (WebSocketDisconnect, asyncio.CancelledError):
        return


@app.websocket('/ws/drone-location')
async def drone_location_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            event = latest_event
            await websocket.send_json(
                {
                    'drone_id': 'DRONE-01',
                    'flight_id': 'FLT-LIVE-01',
                    'timestamp': event['timestamp'],
                    'latitude': event['latitude'],
                    'longitude': event['longitude'],
                    'altitude': event['altitude'],
                    'heading': event['heading'],
                }
            )
            await asyncio.sleep(1)
    except (WebSocketDisconnect, asyncio.CancelledError):
        return
