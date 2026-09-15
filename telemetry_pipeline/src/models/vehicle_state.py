"""
Canonical telemetry model used between the telemetry pipeline
and the backend health/intelligence layer.

This model contains measurements and normalized telemetry.

Health score, alerts and recommendations are intentionally NOT
part of this model because they are derived by the backend.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VehicleState(BaseModel):

    # Reject unexpected fields.
    # This prevents accidental schema drift.
    model_config = ConfigDict(extra="forbid")

    # Identification

    drone_id: str = Field(
        default="DRONE-01",
        min_length=1,
    )

    flight_id: str = Field(
        default="FLT-LIVE-01",
        min_length=1,
    )

    timestamp: datetime

    source_timestamp_ms: Optional[int] = None

    # Position

    latitude: Optional[float] = Field(
        default=None,
        ge=-90,
        le=90,
    )

    longitude: Optional[float] = Field(
        default=None,
        ge=-180,
        le=180,
    )

    altitude: Optional[float] = Field(
        default=None,
        ge=-500,
        le=10000,
    )

    heading: Optional[float] = Field(
        default=None,
        ge=0,
        le=360,
    )

    # Movement

    airspeed: Optional[float] = Field(
        default=None,
        ge=0,
    )

    ground_speed: Optional[float] = Field(
        default=None,
        ge=0,
    )

    vertical_speed: Optional[float] = Field(
        default=None,
        ge=-100,
        le=100,
    )

    flight_mode: Optional[str] = None

    # Battery

    battery_voltage: Optional[float] = Field(
        default=None,
        ge=0,
        le=50,
    )

    battery_current: Optional[float] = Field(
        default=None,
        ge=-1000,
        le=1000,
    )

    battery_percentage: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
    )

    # GPS

    gps_fix: Optional[bool] = None

    gps_satellites: Optional[int] = Field(
        default=None,
        ge=0,
    )

    # Communication

    signal_strength: Optional[float] = Field(
        default=None,
        ge=0,
        le=100,
    )

    # Temperature

    temperature: Optional[float] = Field(
        default=None,
        ge=-40,
        le=125,
    )

    # IMU acceleration

    ax: Optional[float] = Field(
        default=None,
        ge=-100,
        le=100,
    )

    ay: Optional[float] = Field(
        default=None,
        ge=-100,
        le=100,
    )

    az: Optional[float] = Field(
        default=None,
        ge=-100,
        le=100,
    )

    # Derived vibration

    vibration: Optional[float] = Field(
        default=None,
        ge=0,
    )




# from datetime import datetime
# from typing import Optional
# from pydantic import BaseModel, Field, ConfigDict

# class VehicleState(BaseModel):
#     model_config = ConfigDict(extra='forbid')

#     drone_id: str = Field("DRONE-01", min_length=1)
#     flight_id: str = Field("FLT-LIVE-01", min_length=1)
#     timestamp: datetime
#     source_timestamp_ms: Optional[int] = None
    
#     latitude: Optional[float] = Field(None, ge=-90, le=90)
#     longitude: Optional[float] = Field(None, ge=-180, le=180)
#     altitude: Optional[float] = Field(None, ge=-500, le=10000)
#     heading: Optional[float] = Field(None, ge=0, le=360)
    
#     airspeed: Optional[float] = Field(None, ge=0)
#     ground_speed: Optional[float] = Field(None, ge=0)
#     vertical_speed: Optional[float] = Field(None, ge=-100, le=100)
    
#     flight_mode: Optional[str] = None
    
#     battery_voltage: Optional[float] = Field(None, ge=0, le=50)
#     battery_current: Optional[float] = Field(None, ge=-1000, le=1000)
#     battery_percentage: Optional[float] = Field(None, ge=0, le=100)
    
#     gps_fix: Optional[bool] = None
#     gps_satellites: Optional[int] = Field(None, ge=0)
    
#     signal_strength: Optional[float] = Field(None, ge=0, le=100)
#     temperature: Optional[float] = Field(None, ge=-40, le=125)
    
#     ax: Optional[float] = Field(None, ge=-100, le=100)
#     ay: Optional[float] = Field(None, ge=-100, le=100)
#     az: Optional[float] = Field(None, ge=-100, le=100)
    
#     vibration: Optional[float] = None  # temporary deprecated compatibility field
