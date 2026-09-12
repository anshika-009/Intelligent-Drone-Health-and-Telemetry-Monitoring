import os
from datetime import datetime, timezone
from typing import Any
try:
    from pymavlink import mavutil
except ModuleNotFoundError:
    mavutil = None
from app.services.health.engine import calculate_health

SCENARIOS = {
    "normal": {"label": "Live Flight", "description": "Real MAVLink Data."},
    "low_battery": {
        "label": "Low Battery",
        "description": "Battery decreases toward warning thresholds.",
    },
    "gps_loss": {
        "label": "GPS Loss",
        "description": "GPS becomes unavailable mid-flight.",
    },
    "signal_degradation": {
        "label": "Signal Degradation",
        "description": "Communication strength decreases progressively.",
    },
    "motor_vibration": {
        "label": "Motor Vibration",
        "description": "Motor vibration rises, indicating possible bearing wear.",
    },
    "multi_fault": {
        "label": "Multi-Fault",
        "description": "Multiple abnormal streams are correlated in one session.",
    },
}


class Simulator:
    def __init__(self) -> None:
        self.scenario = "live_mavlink"
        self.tick = 0

        self.state: dict[str, Any] = {
            "latitude": 0.0,
            "longitude": 0.0,
            "altitude": 0.0,
            "ground_speed": 0.0,
            "airspeed": 0.0,
            "vertical_speed": 0.0,
            "heading": 0.0,
            "flight_mode": "GUIDED",
            "battery_percentage": 100.0,
            "battery_voltage": 12.6,
            "estimated_remaining_flight_time": 20,
            "signal_strength": 100.0,
            "gps_fix": True,
            "gps_satellites": 10,
            "vibration": 0.0,
            "temperature": 35.0,
            "motor_outputs": [0, 0, 0, 0],
            "ax": 0.0,
            "ay": 0.0,
            "az": 0.0,
        }

        mav_url = os.environ.get("MAVLINK_URL", "udp:host.docker.internal:14550")
        print(f"BRIDGE ONLINE: Connecting to MAVLink stream at {mav_url}", flush=True)
        try:
            self.master = mavutil.mavlink_connection(mav_url) if mavutil else None
        except Exception as e:
            print(f"MAVLink Connection Error: {e}")
            self.master = None

    def set_scenario(self, scenario: str) -> None:
        self.scenario = "live_mavlink"

    def next(self) -> dict[str, Any]:
        self.tick += 1
        s = self.state
        s["timestamp"] = datetime.now(timezone.utc).isoformat()

        if self.master:
            while True:
                msg = self.master.recv_match(blocking=False)
                if not msg:
                    break

                msg_type = msg.get_type()

                if msg_type == "GLOBAL_POSITION_INT":
                    s["latitude"] = msg.lat / 1e7
                    s["longitude"] = msg.lon / 1e7
                    s["altitude"] = msg.relative_alt / 1000.0
                elif msg_type == "SYS_STATUS":
                    s["battery_voltage"] = msg.voltage_battery / 1000.0
                    s["battery_percentage"] = (
                        float(msg.battery_remaining)
                        if msg.battery_remaining >= 0
                        else 0.0
                    )

                elif msg_type == "VFR_HUD":
                    s["heading"] = msg.heading
                    s["airspeed"] = msg.airspeed
                    s["ground_speed"] = msg.groundspeed
                    s["vertical_speed"] = msg.climb

                elif msg_type == "RAW_IMU":
                    s["ax"] = msg.xacc * 0.00981
                    s["ay"] = msg.yacc * 0.00981
                    s["az"] = msg.zacc * 0.00981
                    if hasattr(msg, "temperature") and msg.temperature:
                        s["temperature"] = msg.temperature / 100.0

        event = dict(s)
        event["drone_id"] = "DRONE-01"
        event["flight_id"] = "FLT-LIVE-01"

        try:
            event["health_score"] = calculate_health(event)
        except:
            event["health_score"] = 100

        return event
