"""
Backend telemetry schemas.

All telemetry fields that can become stale are Optional.

None means:

    "The value is currently unavailable/stale."

It does NOT mean zero.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):

    timestamp: datetime

    drone_id: str = "DRONE-01"

    flight_id: str = "FLT-LIVE-01"

    # Position

    latitude: Optional[float] = None

    longitude: Optional[float] = None

    altitude: Optional[float] = None

    # Movement

    ground_speed: Optional[float] = None

    airspeed: Optional[float] = None

    vertical_speed: Optional[float] = None

    heading: Optional[float] = None

    flight_mode: Optional[str] = None

    # Battery

    battery_percentage: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
    )

    battery_voltage: Optional[float] = None

    battery_current: Optional[float] = None

    estimated_remaining_flight_time: Optional[int] = None

    # Communication

    signal_strength: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
    )

    # GPS

    gps_fix: Optional[bool] = None

    gps_satellites: Optional[int] = None

    # IMU / vibration

    ax: Optional[float] = None

    ay: Optional[float] = None

    az: Optional[float] = None

    vibration: Optional[float] = None

    # Temperature

    temperature: Optional[float] = None

    # Motor data

    motor_outputs: Optional[list[float]] = None

    # Derived health

    health_score: Optional[int] = Field(
        default=None,
        ge=0,
        le=100,
    )


class ScenarioRequest(BaseModel):
    """
    Used by the frontend to request a demo/fault scenario.
    """

    scenario: str


# from datetime import datetime
# from typing import Optional
# from pydantic import BaseModel, Field

# class TelemetryEvent(BaseModel):
#     timestamp: datetime
#     drone_id: str = 'DRONE-01'
#     flight_id: str = 'FLT-LIVE-01'
#     latitude: Optional[float] = None
#     longitude: Optional[float] = None
#     altitude: Optional[float] = None
#     ground_speed: Optional[float] = None
#     airspeed: Optional[float] = None
#     vertical_speed: Optional[float] = None
#     heading: Optional[float] = None
#     flight_mode: Optional[str] = None
#     battery_percentage: Optional[float] = Field(default=None, ge=0, le=100)
#     battery_voltage: Optional[float] = None
#     estimated_remaining_flight_time: Optional[int] = None
#     signal_strength: Optional[float] = Field(default=None, ge=0, le=100)
#     gps_fix: Optional[bool] = None
#     gps_satellites: Optional[int] = None
#     vibration: Optional[float] = None
#     temperature: Optional[float] = None
#     motor_outputs: Optional[list[float]] = None
#     health_score: Optional[int] = Field(default=None, ge=0, le=100)

# class ScenarioRequest(BaseModel):
#     scenario: str