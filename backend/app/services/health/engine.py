from typing import Any

def component_health(telemetry: dict[str, Any]) -> dict[str, int]:
    battery = round(max(0, min(100, telemetry['battery_percentage'] + 10)))
    motors = round(max(0, min(100, 100 - telemetry['vibration'] * 42)))
    gps = 98 if telemetry['gps_fix'] else 20
    sensors = round(max(0, min(100, 96 - max(0, telemetry['temperature'] - 55) * 1.4)))
    communication = round(max(0, min(100, telemetry['signal_strength'])))
    return {'battery': battery, 'motors': motors, 'gps': gps, 'sensors': sensors, 'communication': communication}

def calculate_health(telemetry: dict[str, Any]) -> int:
    c = component_health(telemetry)
    return round(c['battery'] * .20 + c['motors'] * .25 + c['gps'] * .20 + c['sensors'] * .15 + c['communication'] * .20)

def explainable_rules(telemetry: dict[str, Any]) -> list[dict[str, Any]]:
    rules = []
    if telemetry['battery_percentage'] < 30:
        rules.append({'id':'battery-low','severity':'WARNING','source':'Battery rule','title':'Battery reserve is low','explanation':'Remaining reserve is approaching the configured mission threshold.','metric':f"{telemetry['battery_percentage']:.0f}%",'recommendation':'Plan a return and recharge the battery before the next flight.'})
    if telemetry['signal_strength'] < 45:
        rules.append({'id':'signal-weak','severity':'WARNING','source':'Communication rule','title':'Communication signal degrading','explanation':'Link reliability is decreasing progressively during this session.','metric':f"{telemetry['signal_strength']:.0f}%",'recommendation':'Prepare Return-To-Home.'})
    if telemetry['vibration'] > .48:
        rules.append({'id':'motor-vibration','severity':'CRITICAL','source':'Motor rule','title':'Motor vibration above baseline','explanation':'Motor vibration has crossed the bearing inspection threshold.','metric':f"{telemetry['vibration']:.2f} g",'recommendation':'Land safely and inspect motor bearing before another extended flight.'})
    if not telemetry['gps_fix']:
        rules.append({'id':'gps-loss','severity':'CRITICAL','source':'GPS rule','title':'GPS fix unavailable','explanation':'The aircraft is not receiving a valid position solution.','metric':'0 satellites','recommendation':'Hold position if safe and initiate Return-To-Home.'})
    if telemetry['temperature'] > 58:
        rules.append({'id':'temperature-high','severity':'WARNING','source':'Temperature rule','title':'Temperature above operating baseline','explanation':'Thermal load is above the normal envelope for this flight.','metric':f"{telemetry['temperature']:.0f} °C",'recommendation':'Reduce load and inspect cooling before another extended flight.'})
    return rules
