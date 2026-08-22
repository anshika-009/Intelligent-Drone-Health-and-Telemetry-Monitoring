from datetime import datetime
from pydantic import BaseModel, Field

class TelemetryEvent(BaseModel):
    timestamp: datetime
    drone_id: str = 'DRONE-01'
    flight_id: str = 'FLT-LIVE-01'
    latitude: float
    longitude: float
    altitude: float
    ground_speed: float
    airspeed: float
    vertical_speed: float
    heading: float
    flight_mode: str
    battery_percentage: float = Field(ge=0, le=100)
    battery_voltage: float
    estimated_remaining_flight_time: int
    signal_strength: float = Field(ge=0, le=100)
    gps_fix: bool
    gps_satellites: int
    vibration: float
    temperature: float
    motor_outputs: list[float]
    health_score: int = Field(ge=0, le=100)

class ScenarioRequest(BaseModel):
    scenario: str

class Credentials(BaseModel):
    email: str
    password: str
    name: str | None = None
