import asyncio
import secrets
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.core.security import hash_password, verify_password
from app.database.session import initialize, persist_telemetry
from app.schemas.telemetry import Credentials, ScenarioRequest
from app.services.health.engine import explainable_rules, component_health
from app.services.telemetry.simulator import Simulator, SCENARIOS

app = FastAPI(title='IDHTM Telemetry API', version='1.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])
simulator = Simulator()
users = {'operator@idhtm.dev': {'name':'Demo Operator','password':hash_password('demo-flight')}}
tokens: dict[str, str] = {}
maintenance = [{'id':'MNT-001','component':'Motor 2','issue':'Potential bearing wear','recommendation':'Inspect motor bearing before next extended flight.','severity':'Medium','status':'Pending','created_at':'2026-08-21T14:50:00Z'}]
flights = [{'id':'FLT-2026-0821-07','date':'21 Aug 2026 · 14:32','duration':'18m 42s','health':92,'alerts':2,'summary':'Stable survey flight. Minor signal fluctuation on descent.'},{'id':'FLT-2026-0820-03','date':'20 Aug 2026 · 09:18','duration':'26m 11s','health':88,'alerts':4,'summary':'Extended inspection flight with rising motor vibration.'},{'id':'FLT-2026-0818-11','date':'18 Aug 2026 · 16:05','duration':'12m 28s','health':97,'alerts':0,'summary':'Nominal mapping flight across the north sector.'}]
@app.on_event('startup')
def startup() -> None: initialize()
@app.get('/api/healthcheck')
def healthcheck(): return {'status':'ok','service':'idhtm-api','time':datetime.now(timezone.utc).isoformat()}
@app.post('/api/auth/register')
def register(credentials: Credentials):
    if credentials.email in users: raise HTTPException(409, 'An operator with this email already exists.')
    if len(credentials.password) < 6: raise HTTPException(422, 'Password must be at least 6 characters.')
    users[credentials.email] = {'name':credentials.name or 'Flight Operator','password':hash_password(credentials.password)}
    token = secrets.token_urlsafe(24); tokens[token] = credentials.email
    return {'token':token,'user':{'email':credentials.email,'name':users[credentials.email]['name']}}
@app.post('/api/auth/login')
def login(credentials: Credentials):
    user = users.get(credentials.email)
    if not user or not verify_password(credentials.password, user['password']): raise HTTPException(401, 'Invalid operator credentials.')
    token = secrets.token_urlsafe(24); tokens[token] = credentials.email
    return {'token':token,'user':{'email':credentials.email,'name':user['name']}}
@app.post('/api/auth/logout')
def logout(): return {'status':'signed_out'}
@app.get('/api/drones')
def drones(): return [{'id':'DRONE-01','name':'DRONE-01','model':'Industrial Survey Mk II','status':'simulator_active','health':simulator.next()['health_score']}]
@app.get('/api/telemetry/scenarios')
def scenarios(): return [{'id':key, **value} for key,value in SCENARIOS.items()]
@app.post('/api/telemetry/scenario')
def set_scenario(request: ScenarioRequest):
    try: simulator.set_scenario(request.scenario)
    except ValueError as error: raise HTTPException(422, str(error))
    return {'scenario':simulator.scenario,'status':'active'}
@app.get('/api/telemetry/latest')
def latest():
    event = simulator.next(); persist_telemetry(event, simulator.scenario); return event
@app.get('/api/health')
def health():
    event = simulator.next(); return {'scenario':simulator.scenario,'score':event['health_score'],'components':component_health(event),'rules':explainable_rules(event)}
@app.get('/api/alerts')
def alerts():
    event = simulator.next(); return [{**rule,'id':f"{rule['id']}-{simulator.tick}",'timestamp':event['timestamp'],'acknowledged':False} for rule in explainable_rules(event)]
@app.post('/api/alerts/{alert_id}/acknowledge')
def acknowledge(alert_id: str): return {'id':alert_id,'acknowledged':True}
@app.get('/api/flights')
def list_flights(): return flights
@app.get('/api/flights/{flight_id}')
def flight(flight_id: str):
    match = next((item for item in flights if item['id'] == flight_id), None)
    if not match: raise HTTPException(404, 'Flight session not found.')
    return {**match,'telemetry':[],'events':[]}
@app.get('/api/maintenance')
def list_maintenance(): return maintenance
@app.post('/api/maintenance')
def create_maintenance(payload: dict):
    item = {'id':f"MNT-{len(maintenance)+1:03d}", 'created_at':datetime.now(timezone.utc).isoformat(), **payload}; maintenance.append(item); return item
@app.patch('/api/maintenance/{item_id}')
def update_maintenance(item_id: str, payload: dict):
    for item in maintenance:
        if item['id'] == item_id: item.update(payload); return item
    raise HTTPException(404, 'Maintenance record not found.')
@app.get('/api/reports')
def reports(): return [{'id':'RPT-FLIGHT-01','type':'Flight summary','title':'Flight summary / FLT-2026-0821-07','status':'ready'},{'id':'RPT-HEALTH-01','type':'Health summary','title':'Health summary / DRONE-01','status':'ready'}]
@app.get('/api/connections')
def connections(): return [{'source':'Simulator','state':'connected','packets_per_second':1,'latency_ms':18,'message_count':simulator.tick,'last_update':datetime.now(timezone.utc).isoformat()},{'source':'Pixhawk / MAVLink','state':'available','packets_per_second':0,'latency_ms':None,'message_count':0,'last_update':None},{'source':'ArduPilot SITL','state':'available','packets_per_second':0,'latency_ms':None,'message_count':0,'last_update':None}]
@app.websocket('/ws/telemetry')
async def telemetry_socket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            event = simulator.next(); persist_telemetry(event, simulator.scenario); await websocket.send_json({'scenario':simulator.scenario,'telemetry':event,'alerts':explainable_rules(event)}); await asyncio.sleep(1)
    except (WebSocketDisconnect, asyncio.CancelledError):
        return
