import joblib
import pandas as pd
import math
from collections import deque

# Load the ML model when the server starts
ml_model = joblib.load('backend/ml_engine/drone_health_iforest.pkl')

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
        # Root Mean Square Acceleration Formula
        a_rms = math.sqrt(ax**2 + ay**2 + az**2)

        if a_rms > 30.0:
            return {
                "vibration_alert": True,
                "rms_value": a_rms,
                "risk": "Severe mechanical failure risk",
            }
        return {"vibration_alert": False, "rms_value": a_rms, "risk": "Normal"}

    def get_ml_health_score(self, vibration, battery, speed):
        # Data ko ML model ke format mein daalo
        data = pd.DataFrame([[vibration, battery, speed]], 
                            columns=['vibration', 'battery_voltage', 'ground_speed'])
        
        # Prediction nikalo: 1 means Normal, -1 means Anomaly/Fault
        prediction = ml_model.predict(data)[0]
        
        if prediction == -1:
            return 40  # ML ne fault pakda hai!
        return 95      # Sab normal hai

    def get_overall_system_state(self, ax, ay, az, current_voltage, ground_speed):
        """Ye master function hai jo backend simulator.py ab direct use karega"""
        motor_status = self.evaluate_motor_health(ax, ay, az)
        battery_status = self.evaluate_battery_state(current_voltage)
        
        # Calculate final AI Health Score using the actual vibration (rms) and battery values
        ai_health = self.get_ml_health_score(motor_status["rms_value"], current_voltage, ground_speed)
        
        return {
            "health_score": ai_health,
            "battery": battery_status,
            "motor": motor_status
        }