from typing import Any, Dict
from src.models.vehicle_state import VehicleState

def adapt_to_backend(state: VehicleState) -> Dict[str, Any]:
    """
    Stateless adapter that converts a canonical VehicleState snapshot into the flat
    dictionary expected by the legacy backend.
    
    WARNING: Schema-safe fallbacks (0.0, False) have been REMOVED because they are 
    semantically dangerous and will trigger backend AI alerts if TTL expires. 
    The downstream schema must accept None/NULL.
    """
    
    output = {
        "drone_id": state.drone_id,
        "flight_id": state.flight_id,
        "timestamp": state.timestamp.isoformat(),
        
        # Real Telemetry Mappings (no dangerous fallbacks)
        "latitude": state.latitude,
        "longitude": state.longitude,
        "altitude": state.altitude,
        "ground_speed": state.ground_speed,
        "airspeed": state.airspeed,
        "vertical_speed": state.vertical_speed,
        "heading": state.heading,
        "battery_percentage": state.battery_percentage,
        "battery_voltage": state.battery_voltage,
        
        # Voltage Compatibility Alias for AI Engine
        "voltage": state.battery_voltage,
        
	"temperature": state.temperature,
	"signal_strength": state.signal_strength,

	"ax": state.ax,
	"ay": state.ay,
        "az": state.az,

	"gps_fix": bool(state.gps_fix) if state.gps_fix is not None else None,
	"gps_satellites": int(state.gps_satellites) if state.gps_satellites is not None else None,
        
        # COMPATIBILITY_PLACEHOLDER - NOT MEASURED DATA
        "flight_mode": "UNKNOWN",
        "vibration": 0.0,
        "motor_outputs": [0, 0, 0, 0],
        "estimated_remaining_flight_time": 20.0
    }
    
    # NOTE: "health_score" is deliberately omitted. It must be injected by the downstream consumer.
    
    return output
