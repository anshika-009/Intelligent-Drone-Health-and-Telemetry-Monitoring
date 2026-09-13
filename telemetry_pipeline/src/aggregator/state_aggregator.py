from datetime import datetime, timezone
from typing import Dict, Any, Callable, Optional

from src.models.vehicle_state import VehicleState

CATEGORY_TTLS = {
    'position': 2.0,
    'velocity': 2.0,
    'attitude': 2.0,
    'battery': 5.0,
    'gps': 5.0,
    'communications': 5.0,
    'imu': 1.0,
    'temperature': 5.0,
    'heartbeat': 3.0,
}

FIELD_TO_CATEGORY = {
    'latitude': 'position', 'longitude': 'position', 'altitude': 'position',
    'airspeed': 'velocity', 'ground_speed': 'velocity', 'vertical_speed': 'velocity',
    'heading': 'attitude',
    'battery_voltage': 'battery', 'battery_percentage': 'battery', 'battery_current': 'battery',
    'gps_fix': 'gps', 'gps_satellites': 'gps',
    'signal_strength': 'communications',
    'ax': 'imu', 'ay': 'imu', 'az': 'imu',
    'temperature': 'temperature',
    'vehicle_type': 'heartbeat', 'autopilot': 'heartbeat', 'base_mode': 'heartbeat',
    'custom_mode': 'heartbeat', 'system_status': 'heartbeat',
}

def default_clock() -> datetime:
    return datetime.now(timezone.utc)

class StateAggregator:
    """
    Merges normalized partial telemetry updates into a comprehensive
    VehicleState representation, handling field TTL/freshness.
    """
    def __init__(self, clock: Optional[Callable[[], datetime]] = None):
        self._clock = clock if clock is not None else default_clock
        self._state: Dict[str, Any] = {}
        self._metadata: Dict[str, Any] = {}
        self._category_update_times: Dict[str, datetime] = {}
        
        self._allowed_fields = set(VehicleState.model_fields.keys())
        
    def update(self, normalized: Dict[str, Any]) -> None:
        """
        Merges new normalized fields into the aggregated state.
        Unknown fields are redirected to metadata.
        Does not mutate the caller's dictionary.
        """
        if not normalized:
            return
            
        now = self._clock()
        updated_categories = set()
        
        for k, v in normalized.items():
            if k in self._allowed_fields:
                self._state[k] = v
            else:
                self._metadata[k] = v
                
            cat = FIELD_TO_CATEGORY.get(k)
            if cat:
                updated_categories.add(cat)
                
        for cat in updated_categories:
            self._category_update_times[cat] = now

    def _is_fresh(self, category: str, now: datetime) -> bool:
        if category not in self._category_update_times:
            return False
        ttl = CATEGORY_TTLS.get(category, 0.0)
        age = (now - self._category_update_times[category]).total_seconds()
        return age <= ttl

    def get_state(self) -> VehicleState:
        """
        Produces the canonical VehicleState object from the current merged data.
        Stale fields are replaced with None.
        Injects the current timezone-aware UTC datetime based on the internal clock.
        Raises ValidationError if the aggregated state is physically invalid.
        """
        now = self._clock()
        state_data: Dict[str, Any] = {}
        
        if 'source_timestamp_ms' in self._state:
            state_data['source_timestamp_ms'] = self._state['source_timestamp_ms']
            
        for k, v in self._state.items():
            if k == 'source_timestamp_ms':
                continue
                
            cat = FIELD_TO_CATEGORY.get(k)
            if cat and self._is_fresh(cat, now):
                state_data[k] = v
            else:
                state_data[k] = None

        state_data['timestamp'] = now
        return VehicleState(**state_data)
        
    @property
    def metadata(self) -> Dict[str, Any]:
        """
        Returns a copy of the non-VehicleState metadata (e.g. heartbeat info),
        excluding stale telemetry fields.
        """
        now = self._clock()
        fresh_metadata = {}
        for k, v in self._metadata.items():
            cat = FIELD_TO_CATEGORY.get(k)
            if cat and self._is_fresh(cat, now):
                fresh_metadata[k] = v
        return fresh_metadata
