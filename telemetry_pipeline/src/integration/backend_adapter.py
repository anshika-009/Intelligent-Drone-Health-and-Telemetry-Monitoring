from typing import Any, Dict
from src.models.vehicle_state import VehicleState

def adapt_to_backend(state: VehicleState) -> Dict[str, Any]:
    """
    Stateless adapter that converts a canonical VehicleState snapshot into the flat
    dictionary expected by the legacy backend.
    
    WARNING: Schema-safe fallbacks (0.0, False) are semantically dangerous and will
    trigger backend AI alerts if TTL expires, but are required to satisfy the legacy
    strict database schemas.
    """
    
    # Safe float fallback helper
    def f_fallback(val: Any) -> float:
        return float(val) if val is not None else 0.0

    output = {
        "drone_id": state.drone_id,
        "flight_id": state.flight_id,
        "timestamp": state.timestamp.isoformat(),
        
        # Real Telemetry Mappings (with dangerous 0.0 fallbacks)
        "latitude": f_fallback(state.latitude),
        "longitude": f_fallback(state.longitude),
        "altitude": f_fallback(state.altitude),
        "ground_speed": f_fallback(state.ground_speed),
        "airspeed": f_fallback(state.airspeed),
        "vertical_speed": f_fallback(state.vertical_speed),
        "heading": f_fallback(state.heading),
        "battery_percentage": f_fallback(state.battery_percentage),
        "battery_voltage": f_fallback(state.battery_voltage),
        
        # Voltage Compatibility Alias for AI Engine
        "voltage": f_fallback(state.battery_voltage),
        
        "temperature": f_fallback(state.temperature),
        "signal_strength": f_fallback(state.signal_strength),
        
        "gps_fix": bool(state.gps_fix) if state.gps_fix is not None else False,
        "gps_satellites": int(state.gps_satellites) if state.gps_satellites is not None else 0,
        
        # COMPATIBILITY_PLACEHOLDER - NOT MEASURED DATA
        "flight_mode": "UNKNOWN",
        "vibration": 0.0,
        "motor_outputs": [0, 0, 0, 0],
        "estimated_remaining_flight_time": 20.0
    }
    
    # NOTE: "health_score" is deliberately omitted. It must be injected by the downstream consumer.
    
    return output
