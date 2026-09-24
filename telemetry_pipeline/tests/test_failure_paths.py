import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta
import sys

from src.orchestrator.pipeline_runner import PipelineRunner, PipelineNotActiveError
from src.source.mavlink_source import MAVLinkConnectionError
from src.parser.mavlink_parser import MAVLinkParser
from src.models.vehicle_state import VehicleState
from src.aggregator.state_aggregator import StateAggregator
from src.integration.backend_adapter import adapt_to_backend

class TestFailurePathsAndIntegrity(unittest.TestCase):

    def setUp(self):
        self.mavutil_patcher = patch('src.source.mavlink_source.mavutil')
        self.mock_mavutil = self.mavutil_patcher.start()
        self.mock_connection = MagicMock()
        self.mock_mavutil.mavlink_connection.return_value = self.mock_connection
        
        self.runner = PipelineRunner('mock:url')

    def tearDown(self):
        self.mavutil_patcher.stop()

    # 1. PipelineRunner Lifecycle Extensions
    def test_start_stop_start_cycle(self):
        self.runner.start()
        self.assertTrue(self.runner.is_active)
        self.runner.stop()
        self.assertFalse(self.runner.is_active)
        self.runner.start()
        self.assertTrue(self.runner.is_active)
        # Should have called connect twice, closed once
        self.assertEqual(self.mock_mavutil.mavlink_connection.call_count, 2)
        self.assertEqual(self.mock_connection.close.call_count, 1)

    # 2. Transport failure propagation
    def test_runner_propagates_connection_error_explicitly(self):
        self.runner.start()
        
        # Simulating MAVLinkSource explicitly raising MAVLinkConnectionError
        self.mock_connection.recv_match.side_effect = Exception("Hardware disconnect")
        
        with self.assertRaises(MAVLinkConnectionError):
            self.runner.poll_once()
            
        self.assertFalse(self.runner.is_active, "Runner should mark itself inactive on disconnect")

    # 3. Empty receive behavior
    def test_empty_receive_preserves_state(self):
        self.runner.start()
        
        # Inject valid message first
        mock_msg = MagicMock()
        mock_msg.get_type.return_value = 'SYS_STATUS'
        mock_msg.voltage_battery = 12500
        mock_msg.battery_remaining = 90
        mock_msg.current_battery = 1500
        self.mock_connection.recv_match.return_value = mock_msg
        self.assertTrue(self.runner.poll_once())
        
        initial_state = self.runner.get_state()
        self.assertEqual(initial_state.battery_voltage, 12.5)

        # Now simulate empty receive
        self.mock_connection.recv_match.return_value = None
        self.assertFalse(self.runner.poll_once())
        
        # Verify state is completely preserved
        preserved_state = self.runner.get_state()
        self.assertEqual(preserved_state.battery_voltage, 12.5)
        self.assertEqual(preserved_state.battery_percentage, 90.0)

    # 4. Unsupported MAVLink messages
    def test_unsupported_message_preserves_state(self):
        self.runner.start()
        
        # Valid update
        valid_msg = MagicMock()
        valid_msg.get_type.return_value = 'VFR_HUD'
        valid_msg.heading = 180
        valid_msg.airspeed = 15
        valid_msg.groundspeed = 14
        valid_msg.climb = -1
        self.mock_connection.recv_match.return_value = valid_msg
        self.assertTrue(self.runner.poll_once())
        
        initial_state = self.runner.get_state()
        self.assertEqual(initial_state.heading, 180.0)
        
        # Unsupported update
        unsupported_msg = MagicMock()
        unsupported_msg.get_type.return_value = 'UNKNOWN_MSG_123'
        self.mock_connection.recv_match.return_value = unsupported_msg
        
        self.assertFalse(self.runner.poll_once())
        
        # Verify no mutation occurred
        preserved_state = self.runner.get_state()
        self.assertEqual(preserved_state.heading, 180.0)

    # 5. Malformed parser input
    def test_parser_malformed_input_documented_behavior(self):
        parser = MAVLinkParser()
        
        # According to the audit, the parser swallows get_type() exceptions
        # and safely returns None. Let's provide an object that crashes get_type().
        class MalformedPayload:
            def get_type(self):
                raise MemoryError("Simulated critical failure")
                
        # The parser currently suppresses this and returns None (known defect, testing documented behavior)
        with self.assertRaises(MemoryError):
            parser.parse(MalformedPayload())

    # 6. Partial telemetry
    def test_partial_telemetry_isolation(self):
        self.runner.start()
        
        # Send SYS_STATUS
        msg1 = MagicMock()
        msg1.get_type.return_value = 'SYS_STATUS'
        msg1.voltage_battery = 12500
        msg1.battery_remaining = 90
        msg1.current_battery = -1
        self.mock_connection.recv_match.return_value = msg1
        self.runner.poll_once()
        
        # Send VFR_HUD (partial update, totally different fields)
        msg2 = MagicMock()
        msg2.get_type.return_value = 'VFR_HUD'
        msg2.heading = 90
        msg2.airspeed = 10
        msg2.groundspeed = 10
        msg2.climb = 0
        self.mock_connection.recv_match.return_value = msg2
        self.runner.poll_once()
        
        state = self.runner.get_state()
        # Battery should still be there (isolation)
        self.assertEqual(state.battery_voltage, 12.5)
        # Heading should be updated
        self.assertEqual(state.heading, 90.0)

    # 7 & 8. TTL expiration and State Recovery
    def test_ttl_stale_and_recovery_cycle(self):
        now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        def mock_clock():
            return now
            
        agg = StateAggregator(clock=mock_clock)
        
        # Fresh update
        agg.update({'battery_voltage': 12.0})
        self.assertEqual(agg.get_state().battery_voltage, 12.0)
        
        # Advance clock by 6 seconds (battery TTL is 5.0)
        now = now + timedelta(seconds=6)
        
        # Field should be expired (None)
        self.assertIsNone(agg.get_state().battery_voltage)
        
        # Recovery: Fresh packet arrives
        agg.update({'battery_voltage': 11.8})
        self.assertEqual(agg.get_state().battery_voltage, 11.8)

    # 9. Timestamp behavior
    def test_timestamp_monotonic_and_timezone_aware(self):
        state = self.runner.get_state()
        self.assertIsNotNone(state.timestamp)
        self.assertEqual(state.timestamp.tzinfo, timezone.utc)
        
        ts1 = state.timestamp
        ts2 = self.runner.get_state().timestamp
        
        self.assertGreaterEqual(ts2, ts1)

    # 10. Adapter isolation
    def test_adapter_isolation_and_determinism(self):
        state = VehicleState(
        timestamp=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        latitude=10.0,
        longitude=20.0,
        battery_voltage=12.0)

        # Convert twice
        dict1 = adapt_to_backend(state)
        dict2 = adapt_to_backend(state)

        # Deterministic
        self.assertEqual(dict1, dict2)

        # Motor outputs are unavailable in the current telemetry pipeline
        self.assertIsNone(dict1['motor_outputs'])
        self.assertIsNone(dict2['motor_outputs'])

        # Ensure VehicleState was not mutated
        self.assertEqual(state.latitude, 10.0)
        self.assertEqual(state.longitude, 20.0)
        self.assertEqual(state.battery_voltage, 12.0)
    # 11. Architectural isolation
    def test_architectural_isolation_no_forbidden_imports(self):
        import sys
        
        # Run through the pipeline modules and check sys.modules
        from src.orchestrator import pipeline_runner
        from src.source import mavlink_source
        from src.parser import mavlink_parser
        from src.normalizer import mavlink_normalizer
        from src.aggregator import state_aggregator
        from src.models import vehicle_state
        from src.integration import backend_adapter
        
        forbidden_modules = [
            'fastapi',
            'app.api',
            'app.database',
            'app.services.health',
            'backend.app'
        ]
        
        for module_name in sys.modules.keys():
            for forbidden in forbidden_modules:
                self.assertFalse(
                    module_name == forbidden or module_name.startswith(f"{forbidden}."),
                    f"Architectural violation: telemetry_pipeline imported forbidden module {module_name}"
                )

if __name__ == '__main__':
    unittest.main()

