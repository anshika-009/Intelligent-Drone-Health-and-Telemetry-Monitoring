from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class VehicleState(BaseModel):
    model_config = ConfigDict(extra='forbid')

    drone_id: str = Field("DRONE-01", min_length=1)
    flight_id: str = Field("FLT-LIVE-01", min_length=1)
    timestamp: datetime
    source_timestamp_ms: Optional[int] = None
    
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    altitude: Optional[float] = Field(None, ge=-500, le=10000)
    heading: Optional[float] = Field(None, ge=0, le=360)
    
    airspeed: Optional[float] = Field(None, ge=0)
    ground_speed: Optional[float] = Field(None, ge=0)
    vertical_speed: Optional[float] = Field(None, ge=-100, le=100)
    
    flight_mode: Optional[str] = None
    
    battery_voltage: Optional[float] = Field(None, ge=0, le=50)
    battery_current: Optional[float] = Field(None, ge=-1000, le=1000)
    battery_percentage: Optional[float] = Field(None, ge=0, le=100)
    
    gps_fix: Optional[bool] = None
    gps_satellites: Optional[int] = Field(None, ge=0)
    
    signal_strength: Optional[float] = Field(None, ge=0, le=100)
    temperature: Optional[float] = Field(None, ge=-40, le=125)
    
    ax: Optional[float] = Field(None, ge=-100, le=100)
    ay: Optional[float] = Field(None, ge=-100, le=100)
    az: Optional[float] = Field(None, ge=-100, le=100)
    
    vibration: Optional[float] = None  # temporary deprecated compatibility field
