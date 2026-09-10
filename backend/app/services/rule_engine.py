import math
from collections import deque

class IDHTMRuleEngine:
    def __init__(self, telemetry_rate_hz=5):
        # Agar telemetry 5 baar per second aati hai, toh 2 sec = 10 samples
        window_size = 2 * telemetry_rate_hz 
        self.voltage_window = deque(maxlen=window_size)
        
    def get_filtered_voltage(self, current_voltage):
        """Applies a 2-second moving average filter to battery voltage"""
        self.voltage_window.append(current_voltage)
        return sum(self.voltage_window) / len(self.voltage_window)
    
    def evaluate_battery_state(self, current_voltage):
        avg_vpack = self.get_filtered_voltage(current_voltage)
        
        # 3S LiPo Degradation Limits
        if avg_vpack > 11.10:
            return {"status": "NORMAL", "action": "Normal flight operations"}
        elif 10.80 <= avg_vpack <= 11.00:
            return {"status": "WARNING", "action": "Restrict high-throttle climbs"}
        elif 10.20 < avg_vpack <= 10.50:
            return {"status": "CRITICAL", "action": "Trigger automated RTL"}
        elif avg_vpack <= 10.20:
            return {"status": "EMERGENCY", "action": "Immediate emergency landing"}
        
        return {"status": "STABLE", "action": "Monitoring"}

    def evaluate_motor_health(self, ax, ay, az):
        # Root Mean Square Acceleration Formula[cite: 1]
        a_rms = math.sqrt(ax**2 + ay**2 + az**2)
        
        if a_rms > 30.0:
            return {"vibration_alert": True, "rms_value": a_rms, "risk": "Severe mechanical failure risk"}
        return {"vibration_alert": False, "rms_value": a_rms, "risk": "Normal"}