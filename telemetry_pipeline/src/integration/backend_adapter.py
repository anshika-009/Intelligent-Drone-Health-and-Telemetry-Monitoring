"""
Backend Adapter
---------------

Converts canonical VehicleState into the dictionary expected
by the FastAPI backend.

IMPORTANT:

    This file does NOT calculate health.

    Health is calculated later by:
        backend/app/services/health/engine.py

This adapter is only responsible for data translation.
"""

import math
from typing import Any

from src.models.vehicle_state import VehicleState


# Standard gravitational acceleration.
GRAVITY = 9.80665


def calculate_vibration(
    ax: float | None,
    ay: float | None,
    az: float | None,
) -> float | None:
    """
    Calculates a simple acceleration-based vibration proxy.

    IMPORTANT:
        This is NOT a true motor vibration sensor.

        The current MAVLink pipeline provides IMU acceleration,
        so we derive a proxy value for the prototype.

    Later, if a dedicated VIBRATION message is integrated,
    this function should be replaced by that measured value.
    """

    if ax is None or ay is None or az is None:
        return None

    acceleration_magnitude = math.sqrt(
        ax**2 +
        ay**2 +
        az**2
    )

    # Remove approximately 1 g of gravity.
    vibration_ms2 = abs(
        acceleration_magnitude - GRAVITY
    )

    # Convert m/s² to g.
    vibration_g = vibration_ms2 / GRAVITY

    return round(vibration_g, 4)


def adapt_to_backend(
    state: VehicleState,
) -> dict[str, Any]:
    """
    Converts VehicleState into the backend telemetry dictionary.
    """

    vibration = calculate_vibration(
        state.ax,
        state.ay,
        state.az,
    )

    return {
        # Identification

        "drone_id": state.drone_id,

        "flight_id": state.flight_id,

        "timestamp": state.timestamp.isoformat(),

        # Position

        "latitude": state.latitude,

        "longitude": state.longitude,

        "altitude": state.altitude,

        # Movement

        "ground_speed": state.ground_speed,

        "airspeed": state.airspeed,

        "vertical_speed": state.vertical_speed,

        "heading": state.heading,

        "flight_mode": state.flight_mode,

        # Battery

        "battery_percentage": state.battery_percentage,

        "battery_voltage": state.battery_voltage,

        "battery_current": state.battery_current,

        # Legacy alias used by some existing backend code.
        "voltage": state.battery_voltage,

        # GPS

        "gps_fix": state.gps_fix,

        "gps_satellites": state.gps_satellites,

        # Communication

        "signal_strength": state.signal_strength,

        # IMU

        "ax": state.ax,

        "ay": state.ay,

        "az": state.az,

        # Temperature

        "temperature": state.temperature,

        # Derived vibration

        "vibration": vibration,

        # Remaining flight time

        # This is only an estimate.
        # It should NOT be presented as an exact measurement.
        "estimated_remaining_flight_time": (
            round(state.battery_percentage * 0.20)
            if state.battery_percentage is not None
            else None
        ),

        # Motor outputs are not currently available from the
        # canonical telemetry pipeline.
        #
        # DO NOT create fake motor values.
        "motor_outputs": None,

        # Health is intentionally omitted.
        #
        # The backend health engine calculates it.
    }




# from typing import Any, Dict
# from src.models.vehicle_state import VehicleState

# def adapt_to_backend(state: VehicleState) -> Dict[str, Any]:
#     """
#     Stateless adapter that converts a canonical VehicleState snapshot into the flat
#     dictionary expected by the legacy backend.
    
#     WARNING: Schema-safe fallbacks (0.0, False) have been REMOVED because they are 
#     semantically dangerous and will trigger backend AI alerts if TTL expires. 
#     The downstream schema must accept None/NULL.
#     """
    
#     output = {
#         "drone_id": state.drone_id,
#         "flight_id": state.flight_id,
#         "timestamp": state.timestamp.isoformat(),
        
#         # Real Telemetry Mappings (no dangerous fallbacks)
#         "latitude": state.latitude,
#         "longitude": state.longitude,
#         "altitude": state.altitude,
#         "ground_speed": state.ground_speed,
#         "airspeed": state.airspeed,
#         "vertical_speed": state.vertical_speed,
#         "heading": state.heading,
#         "battery_percentage": state.battery_percentage,
#         "battery_voltage": state.battery_voltage,
        
#         # Voltage Compatibility Alias for AI Engine
#         "voltage": state.battery_voltage,
        
# 	"temperature": state.temperature,
# 	"signal_strength": state.signal_strength,

# 	"ax": state.ax,
# 	"ay": state.ay,
#         "az": state.az,

# 	"gps_fix": bool(state.gps_fix) if state.gps_fix is not None else None,
# 	"gps_satellites": int(state.gps_satellites) if state.gps_satellites is not None else None,
        
#         # COMPATIBILITY_PLACEHOLDER - NOT MEASURED DATA
#         "flight_mode": "UNKNOWN",
#         "vibration": 0.0,
#         "motor_outputs": [0, 0, 0, 0],
#         "estimated_remaining_flight_time": 20.0
#     }
    
#     # NOTE: "health_score" is deliberately omitted. It must be injected by the downstream consumer.
    
#     return output
