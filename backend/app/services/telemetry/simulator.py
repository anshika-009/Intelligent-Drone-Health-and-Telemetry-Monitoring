import math
from datetime import datetime, timezone
from typing import Any
from app.services.health.engine import calculate_health

SCENARIOS = {
    'normal': {'label':'Normal Flight','description':'Stable telemetry across all systems.'},
    'low_battery': {'label':'Low Battery','description':'Battery decreases toward warning thresholds.'},
    'gps_loss': {'label':'GPS Loss','description':'GPS becomes unavailable mid-flight.'},
    'signal_degradation': {'label':'Signal Degradation','description':'Communication strength decreases progressively.'},
    'motor_vibration': {'label':'Motor Vibration','description':'Motor vibration rises, indicating possible bearing wear.'},
    'multi_fault': {'label':'Multi-Fault','description':'Multiple abnormal streams are correlated in one session.'},
}

class Simulator: 
    def __init__(self) -> None:
        self.scenario = 'normal'
        self.tick = 0
        self.state: dict[str, Any] = {'latitude':37.7749,'longitude':-122.4194,'altitude':124.0,'ground_speed':42.0,'airspeed':43.0,'vertical_speed':1.8,'heading':274.0,'flight_mode':'AUTO','battery_percentage':87.0,'battery_voltage':23.8,'estimated_remaining_flight_time':18,'signal_strength':92.0,'gps_fix':True,'gps_satellites':14,'vibration':.18,'temperature':38.0,'motor_outputs':[72,71,73,72]}
    def set_scenario(self, scenario: str) -> None:
        if scenario not in SCENARIOS: raise ValueError('Unknown simulator scenario')
        self.scenario, self.tick = scenario, 0
        self.state.update({'battery_percentage':87.0,'signal_strength':92.0,'gps_fix':True,'gps_satellites':14,'vibration':.18,'temperature':38.0})
    def next(self) -> dict[str, Any]:
        self.tick += 1
        t = self.tick
        s = self.state
        s['timestamp'] = datetime.now(timezone.utc).isoformat()
        s['altitude'] = max(74, min(162, 124 + math.sin(t / 3.2) * 20))
        s['ground_speed'] = max(18, 42 + math.sin(t / 2) * 7)
        s['airspeed'] = s['ground_speed'] + 1
        s['vertical_speed'] = math.sin(t / 1.6) * 2
        s['latitude'] = 37.7749 + math.sin(t / 12) * .0018 + math.sin(t / 4.5) * .00025
        s['longitude'] = -122.4194 + math.cos(t / 13) * .0022 + math.sin(t / 5.5) * .0003
        s['battery_percentage'] = max(15, s['battery_percentage'] - (.18 if self.scenario in ('low_battery','multi_fault') else .035))
        s['signal_strength'] = max(24, s['signal_strength'] - (.22 if self.scenario in ('signal_degradation','multi_fault') else 0) + math.sin(t/2.2)*.6)
        s['vibration'] = min(.86, s['vibration'] + (.012 if self.scenario in ('motor_vibration','multi_fault') else .002) + abs(math.sin(t/3))* .006)
        s['gps_fix'] = not (self.scenario == 'gps_loss' or (self.scenario == 'multi_fault' and t % 9 > 4))
        s['gps_satellites'] = 14 if s['gps_fix'] else 0
        s['temperature'] = min(74, s['temperature'] + (.02 if self.scenario == 'multi_fault' else 0) + math.sin(t/3)*.05)
        s['estimated_remaining_flight_time'] = max(5, round(s['battery_percentage'] * .21))
        event = dict(s)
        event['drone_id'] = 'DRONE-01'
        event['flight_id'] = 'FLT-LIVE-01'
        event['health_score'] = calculate_health(event)
        return event
