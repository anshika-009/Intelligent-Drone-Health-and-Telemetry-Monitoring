import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import sys

from src.orchestrator.pipeline_runner import PipelineRunner
from src.aggregator.state_aggregator import StateAggregator
from src.models.vehicle_state import VehicleState

# Helper to mock an arbitrary MAVLink message since pymavlink is absent
def create_mock_msg(msg_type, **kwargs):
    msg = MagicMock()
    msg.get_type.return_value = msg_type
    for k, v in kwargs.items():
        setattr(msg, k, v)
    return msg

class TestProtocolIntegration(unittest.TestCase):

    def setUp(self):
        self.mavutil_patcher = patch('src.source.mavlink_source.mavutil')
        self.mock_mavutil = self.mavutil_patcher.start()
        self.mock_connection = MagicMock()
        self.mock_mavutil.mavlink_connection.return_value = self.mock_connection
        
        # Patch the aggregator clock so we can manually simulate time passing
        self.current_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        def mock_clock():
            return self.current_time
            
        self.runner = PipelineRunner('mock:url')
        self.runner.aggregator._clock = mock_clock

    def tearDown(self):
        self.mavutil_patcher.stop()
        
    def advance_time(self, seconds):
        self.current_time += timedelta(seconds=seconds)

    # 4 & 6. GPS SEMANTIC TEST
    def test_gps_semantics(self):
        self.runner.start()
        
        # Case A: Valid GPS (fix_type >= 3)
        msg_valid = create_mock_msg('GPS_RAW_INT', fix_type=3, satellites_visible=10, 
                                    lat=450000000, lon=-1200000000, relative_alt=100000, time_usec=123)
        self.mock_connection.recv_match.return_value = msg_valid
        self.assertTrue(self.runner.poll_once())
        
        state = self.runner.get_state()
        self.assertTrue(state.gps_fix)
        self.assertEqual(state.gps_satellites, 10)
        
        # Case B: Degraded / no GPS fix (fix_type < 3)
        msg_degraded = create_mock_msg('GPS_RAW_INT', fix_type=2, satellites_visible=4)
        self.mock_connection.recv_match.return_value = msg_degraded
        self.assertTrue(self.runner.poll_once())
        
        state2 = self.runner.get_state()
        self.assertFalse(state2.gps_fix, "GPS fix_type=2 should yield gps_fix=False")
        self.assertEqual(state2.gps_satellites, 4)
        
        # Case C: GPS message disappears (exceeds TTL)
        self.mock_connection.recv_match.return_value = None
        self.advance_time(6.0) # GPS TTL is 5.0
        self.assertFalse(self.runner.poll_once())
        
        state3 = self.runner.get_state()
        self.assertIsNone(state3.gps_fix, "Stale GPS should yield None, not False")
        self.assertIsNone(state3.gps_satellites)

    # 7. BATTERY TEST
    def test_battery_semantics(self):
        self.runner.start()
        
        msg_batt = create_mock_msg('SYS_STATUS', voltage_battery=12600, battery_remaining=85)
        self.mock_connection.recv_match.return_value = msg_batt
        self.assertTrue(self.runner.poll_once())
        
        state = self.runner.get_state()
        self.assertEqual(state.battery_voltage, 12.6)
        self.assertEqual(state.battery_percentage, 85.0)
        
        self.mock_connection.recv_match.return_value = None
        self.advance_time(6.0) # Battery TTL is 5.0
        self.assertFalse(self.runner.poll_once())
        
        state2 = self.runner.get_state()
        self.assertIsNone(state2.battery_voltage)
        self.assertIsNone(state2.battery_percentage)

    # 8. RADIO / SIGNAL TEST
    def test_radio_semantics(self):
        self.runner.start()
        
        # Mid-range RSSI
        msg_radio = create_mock_msg('RADIO_STATUS', rssi=127)
        self.mock_connection.recv_match.return_value = msg_radio
        self.assertTrue(self.runner.poll_once())
        
        state = self.runner.get_state()
        self.assertEqual(state.signal_strength, 50.0)
        
        # Expiry
        self.mock_connection.recv_match.return_value = None
        self.advance_time(6.0) # Comms TTL is 5.0
        self.runner.poll_once()
        
        state2 = self.runner.get_state()
        self.assertIsNone(state2.signal_strength)

    # 9. IMU / TEMPERATURE TEST
    def test_imu_semantics(self):
        self.runner.start()
        
        msg_imu = create_mock_msg('RAW_IMU', xacc=1000, yacc=2000, zacc=-1000, temperature=3500)
        self.mock_connection.recv_match.return_value = msg_imu
        self.assertTrue(self.runner.poll_once())
        
        state = self.runner.get_state()
        # Normalizer uses * 0.00981
        self.assertAlmostEqual(state.ax, 9.81)
        self.assertAlmostEqual(state.ay, 19.62)
        self.assertAlmostEqual(state.az, -9.81)
        # Normalizer uses / 100.0
        self.assertEqual(state.temperature, 35.0)
        
        # Ensure vibration is not magically calculated (must remain None based on architecture)
        self.assertIsNone(state.vibration)

    # 10. PARTIAL TELEMETRY TEST
    def test_partial_telemetry_isolation(self):
        self.runner.start()
        
        # Send GPS & Battery
        msg_gps = create_mock_msg('GLOBAL_POSITION_INT', lat=100000000, lon=100000000)
        msg_batt = create_mock_msg('SYS_STATUS', voltage_battery=12000)
        
        self.mock_connection.recv_match.return_value = msg_gps
        self.runner.poll_once()
        self.mock_connection.recv_match.return_value = msg_batt
        self.runner.poll_once()
        
        state1 = self.runner.get_state()
        self.assertEqual(state1.latitude, 10.0)
        self.assertEqual(state1.battery_voltage, 12.0)
        
        # Advance 3 seconds. Position TTL is 2.0s, Battery TTL is 5.0s.
        self.advance_time(3.0)
        self.mock_connection.recv_match.return_value = None
        self.runner.poll_once()
        
        state2 = self.runner.get_state()
        # GPS should be stale, Battery should be fresh
        self.assertIsNone(state2.latitude, "GPS should be expired")
        self.assertEqual(state2.battery_voltage, 12.0, "Battery should still be fresh")

    # 11. MALFORMED BYTE TESTING
    def test_malformed_input_safety(self):
        self.runner.start()
        
        # Currently the parser swallows get_type() exceptions. We simulate a completely garbage object.
        class GarbageObject:
            def get_type(self):
                raise AttributeError("Corrupt bytes")
                
        self.mock_connection.recv_match.return_value = GarbageObject()
        self.assertFalse(self.runner.poll_once(), "Malformed input should be safely rejected")

    # 14. STATE INTEGRITY
    def test_cross_field_contamination_prevention(self):
        self.runner.start()
        
        # Send Battery
        self.mock_connection.recv_match.return_value = create_mock_msg('SYS_STATUS', voltage_battery=11500)
        self.runner.poll_once()
        
        # Send IMU
        self.mock_connection.recv_match.return_value = create_mock_msg('RAW_IMU', xacc=0)
        self.runner.poll_once()
        
        # Advance 1.5 seconds. IMU TTL is 1.0s, Battery is 5.0s
        self.advance_time(1.5)
        
        # Send GPS
        self.mock_connection.recv_match.return_value = create_mock_msg('GLOBAL_POSITION_INT', lat=0)
        self.runner.poll_once()
        
        state = self.runner.get_state()
        self.assertEqual(state.battery_voltage, 11.5, "Battery should survive")
        self.assertIsNone(state.ax, "IMU should expire")
        self.assertIsNotNone(state.latitude, "GPS should be fresh")

if __name__ == '__main__':
    unittest.main()

