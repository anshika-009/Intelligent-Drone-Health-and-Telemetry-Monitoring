import unittest
from unittest.mock import MagicMock, patch

from src.orchestrator.pipeline_runner import PipelineRunner, PipelineNotActiveError
from src.source.mavlink_source import MAVLinkConnectionError
from src.models.vehicle_state import VehicleState

class TestPipelineRunner(unittest.TestCase):
    def setUp(self):
        self.mavutil_patcher = patch('src.source.mavlink_source.mavutil')
        self.mock_mavutil = self.mavutil_patcher.start()
        
        self.mock_connection = MagicMock()
        self.mock_mavutil.mavlink_connection.return_value = self.mock_connection
        
        self.runner = PipelineRunner('mock:url')

    def tearDown(self):
        self.mavutil_patcher.stop()

    def test_00_initial_state_is_inactive(self):
        self.assertFalse(self.runner.is_active)
        self.mock_mavutil.mavlink_connection.assert_not_called()

    def test_01_start_connects_source(self):
        self.runner.start()
        self.mock_mavutil.mavlink_connection.assert_called_once_with('mock:url')
        self.assertTrue(self.runner.is_active)
        
    def test_01b_start_is_idempotent(self):
        self.runner.start()
        self.runner.start()
        # Ensure connection logic is not repeatedly called if active
        self.mock_mavutil.mavlink_connection.assert_called_once_with('mock:url')

    def test_02_stop_closes_source(self):
        self.runner.start()
        self.runner.stop()
        self.mock_connection.close.assert_called_once()
        self.assertFalse(self.runner.is_active)
        
    def test_02b_stop_is_idempotent(self):
        self.runner.start()
        self.runner.stop()
        self.runner.stop()
        self.mock_connection.close.assert_called_once()
        self.assertFalse(self.runner.is_active)

    def test_03_poll_once_before_start_raises_error(self):
        with self.assertRaises(PipelineNotActiveError):
            self.runner.poll_once()
            
    def test_03b_poll_once_after_stop_raises_error(self):
        self.runner.start()
        self.runner.stop()
        with self.assertRaises(PipelineNotActiveError):
            self.runner.poll_once()

    def test_04_poll_once_no_message(self):
        self.runner.start()
        self.mock_connection.recv_match.return_value = None
        
        result = self.runner.poll_once()
        self.assertFalse(result)
        self.mock_connection.recv_match.assert_called_once_with(blocking=False)

    def test_05_poll_once_valid_message_routed(self):
        self.runner.start()
        
        # Create a mock SYS_STATUS message
        mock_msg = MagicMock()
        mock_msg.get_type.return_value = 'SYS_STATUS'
        mock_msg.voltage_battery = 12500
        mock_msg.battery_remaining = 90
        mock_msg.current_battery = 1500
        
        self.mock_connection.recv_match.return_value = mock_msg
        
        result = self.runner.poll_once()
        
        self.assertTrue(result)
        
        state = self.runner.get_state()
        self.assertAlmostEqual(state.battery_voltage, 12.5)
        self.assertEqual(state.battery_percentage, 90.0)
        self.assertAlmostEqual(state.battery_current, 15.0)

    def test_06_unsupported_message_safely_ignored(self):
        self.runner.start()
        
        mock_msg = MagicMock()
        mock_msg.get_type.return_value = 'COMMAND_ACK'
        self.mock_connection.recv_match.return_value = mock_msg
        
        result = self.runner.poll_once()
        self.assertFalse(result)

    def test_07_normalization_none_safely_ignored(self):
        self.runner.start()
        
        mock_msg = MagicMock()
        mock_msg.get_type.return_value = 'SYS_STATUS'
        del mock_msg.voltage_battery
        del mock_msg.battery_remaining
        del mock_msg.current_battery
        
        self.mock_connection.recv_match.return_value = mock_msg
        
        result = self.runner.poll_once()
        self.assertFalse(result)

    def test_08_connection_error_propagates(self):
        self.runner.start()
        
        self.mock_connection.recv_match.side_effect = Exception("Fatal socket error")
        
        with self.assertRaises(MAVLinkConnectionError):
            self.runner.poll_once()
            
        self.assertFalse(self.runner.is_active)

    def test_09_get_state_returns_vehicle_state(self):
        state = self.runner.get_state()
        self.assertIsInstance(state, VehicleState)
        self.assertEqual(state.drone_id, "DRONE-01")

if __name__ == '__main__':
    unittest.main()
