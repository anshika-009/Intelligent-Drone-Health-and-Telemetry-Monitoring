import unittest
from datetime import datetime, timezone, timedelta
from pydantic import ValidationError

from src.aggregator.state_aggregator import StateAggregator
from src.models.vehicle_state import VehicleState

class TestStateAggregator(unittest.TestCase):
    def setUp(self):
        # We start tests at a deterministic UTC time
        self.current_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.aggregator = StateAggregator(clock=self._mock_clock)

    def _mock_clock(self):
        return self.current_time

    def _advance_time(self, seconds: float):
        self.current_time += timedelta(seconds=seconds)

    # ---------------------------------------------
    # Step 5A Preservation Tests (19, 20)
    # ---------------------------------------------
    def test_20_empty_aggregator_produces_valid_state(self):
        state = self.aggregator.get_state()
        self.assertIsInstance(state, VehicleState)
        self.assertEqual(state.drone_id, "DRONE-01")
        self.assertEqual(state.flight_id, "FLT-LIVE-01")
        self.assertEqual(state.timestamp, self.current_time)
        self.assertIsNone(state.latitude)

    def test_19_existing_step5a_behavior(self):
        self.aggregator.update({"latitude": 12.5, "longitude": 77.0})
        self.aggregator.update({"altitude": 100.0})
        state = self.aggregator.get_state()
        self.assertEqual(state.latitude, 12.5)
        self.assertEqual(state.longitude, 77.0)
        self.assertEqual(state.altitude, 100.0)

    # ---------------------------------------------
    # Freshness / TTL Tests (1-18)
    # ---------------------------------------------
    def test_01_fresh_immediately_after_update(self):
        self.aggregator.update({"latitude": 12.5})
        state = self.aggregator.get_state()
        self.assertEqual(state.latitude, 12.5)

    def test_02_position_becomes_stale(self):
        self.aggregator.update({"latitude": 12.5, "longitude": 77.0})
        self._advance_time(2.1) # Position TTL is 2.0
        state = self.aggregator.get_state()
        self.assertIsNone(state.latitude)
        self.assertIsNone(state.longitude)

    def test_03_position_remains_fresh_within_ttl(self):
        self.aggregator.update({"latitude": 12.5})
        self._advance_time(1.9)
        state = self.aggregator.get_state()
        self.assertEqual(state.latitude, 12.5)

    def test_04_velocity_ttl(self):
        self.aggregator.update({"airspeed": 15.0})
        self._advance_time(2.1) # Velocity TTL is 2.0
        state = self.aggregator.get_state()
        self.assertIsNone(state.airspeed)

    def test_05_battery_ttl(self):
        self.aggregator.update({"battery_voltage": 11.5})
        self._advance_time(4.9)
        self.assertEqual(self.aggregator.get_state().battery_voltage, 11.5)
        self._advance_time(0.2) # > 5.0
        self.assertIsNone(self.aggregator.get_state().battery_voltage)

    def test_06_gps_ttl(self):
        self.aggregator.update({"gps_fix": True})
        self._advance_time(5.1)
        self.assertIsNone(self.aggregator.get_state().gps_fix)

    def test_07_imu_ttl(self):
        self.aggregator.update({"ax": 1.0})
        self._advance_time(1.1)
        self.assertIsNone(self.aggregator.get_state().ax)

    def test_08_temperature_ttl(self):
        self.aggregator.update({"temperature": 35.0})
        self._advance_time(5.1)
        self.assertIsNone(self.aggregator.get_state().temperature)

    def test_09_communications_ttl(self):
        self.aggregator.update({"signal_strength": 90.0})
        self._advance_time(5.1)
        self.assertIsNone(self.aggregator.get_state().signal_strength)

    def test_10_heartbeat_ttl(self):
        self.aggregator.update({"vehicle_type": 2})
        self._advance_time(3.1)
        self.assertNotIn("vehicle_type", self.aggregator.metadata)

    def test_11_independent_category_freshness(self):
        self.aggregator.update({"latitude": 12.5}) # position, TTL 2
        self._advance_time(1.0)
        self.aggregator.update({"battery_voltage": 11.5}) # battery, TTL 5
        
        self._advance_time(1.1) # Time elapsed: position=2.1, battery=1.1
        
        state = self.aggregator.get_state()
        self.assertIsNone(state.latitude) # position stale
        self.assertEqual(state.battery_voltage, 11.5) # battery fresh

    def test_12_partial_category_update(self):
        self.aggregator.update({"latitude": 12.5, "longitude": 77.0, "altitude": 100.0})
        self._advance_time(1.5)
        
        # Partial update refreshes the whole category
        self.aggregator.update({"latitude": 12.6}) 
        self._advance_time(1.5) # Time elapsed since first update = 3.0s, since partial = 1.5s
        
        state = self.aggregator.get_state()
        # Because altitude/longitude weren't overwritten but their category was refreshed, they persist
        self.assertEqual(state.latitude, 12.6)
        self.assertEqual(state.longitude, 77.0)
        self.assertEqual(state.altitude, 100.0)

    def test_13_refresh_after_stale(self):
        self.aggregator.update({"latitude": 12.5})
        self._advance_time(2.5) # stale
        self.assertIsNone(self.aggregator.get_state().latitude)
        
        self.aggregator.update({"latitude": 13.0}) # fresh again
        self.assertEqual(self.aggregator.get_state().latitude, 13.0)

    def test_14_explicit_none(self):
        self.aggregator.update({"battery_voltage": 11.5})
        self.aggregator.update({"battery_voltage": None}) # explicit none
        
        state = self.aggregator.get_state()
        self.assertIsNone(state.battery_voltage)

    def test_15_unknown_metadata(self):
        self.aggregator.update({"vehicle_type": 2, "latitude": 12.5})
        state = self.aggregator.get_state()
        self.assertEqual(state.latitude, 12.5)
        self.assertIn("vehicle_type", self.aggregator.metadata)
        with self.assertRaises(AttributeError):
            getattr(state, "vehicle_type")

    def test_16_vehicle_state_timestamp(self):
        self.aggregator.update({"latitude": 12.5})
        state = self.aggregator.get_state()
        self.assertEqual(state.timestamp, self.current_time)
        self.assertEqual(state.timestamp.tzinfo, timezone.utc)

    def test_17_source_timestamp_ms(self):
        self.aggregator.update({"source_timestamp_ms": 123456789})
        self._advance_time(100.0) # Should not go stale
        state = self.aggregator.get_state()
        self.assertEqual(state.source_timestamp_ms, 123456789)
        self.assertEqual(state.timestamp, self.current_time)

    def test_18_no_real_sleeping(self):
        # We've been using self._advance_time without sleep.
        # This asserts our injected clock is being respected internally.
        self.aggregator.update({"latitude": 12.5})
        self.assertEqual(self.aggregator._category_update_times['position'], self.current_time)

if __name__ == '__main__':
    unittest.main()
