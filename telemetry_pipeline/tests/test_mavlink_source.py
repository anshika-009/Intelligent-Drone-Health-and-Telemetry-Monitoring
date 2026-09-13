import os
import unittest
from unittest.mock import MagicMock, patch

from src.source.mavlink_source import MAVLinkSource, MAVLinkConnectionError

class TestMAVLinkSource(unittest.TestCase):
    def setUp(self):
        # We patch mavutil to ensure tests run even without pymavlink installed locally
        self.mavutil_patcher = patch('src.source.mavlink_source.mavutil')
        self.mock_mavutil = self.mavutil_patcher.start()
        
        # Setup mock connection object returned by mavlink_connection
        self.mock_connection = MagicMock()
        self.mock_mavutil.mavlink_connection.return_value = self.mock_connection
        
    def tearDown(self):
        self.mavutil_patcher.stop()

    def test_01_default_url_configuration(self):
        # Temporarily clear MAVLINK_URL to test fallback
        original_url = os.environ.get('MAVLINK_URL')
        if 'MAVLINK_URL' in os.environ:
            del os.environ['MAVLINK_URL']
            
        source = MAVLinkSource()
        self.assertEqual(source.connection_string, 'udp:host.docker.internal:14550')
        
        # Test environment variable override
        os.environ['MAVLINK_URL'] = 'tcp:127.0.0.1:5760'
        source2 = MAVLinkSource()
        self.assertEqual(source2.connection_string, 'tcp:127.0.0.1:5760')
        
        # Restore environment
        if original_url is not None:
            os.environ['MAVLINK_URL'] = original_url
        else:
            del os.environ['MAVLINK_URL']

    def test_02_explicit_url_configuration(self):
        source = MAVLinkSource('udp:192.168.1.2:14550')
        self.assertEqual(source.connection_string, 'udp:192.168.1.2:14550')

    def test_03_connect_lifecycle(self):
        source = MAVLinkSource('mock:connection')
        self.assertFalse(source.is_open)
        
        source.connect()
        self.mock_mavutil.mavlink_connection.assert_called_once_with('mock:connection')
        self.assertTrue(source.is_open)

    def test_04_connect_failure(self):
        self.mock_mavutil.mavlink_connection.side_effect = Exception("Mock connection failed")
        
        source = MAVLinkSource('mock:connection')
        with self.assertRaises(MAVLinkConnectionError):
            source.connect()
            
        self.assertFalse(source.is_open)

    def test_05_close_lifecycle(self):
        source = MAVLinkSource('mock:connection')
        source.connect()
        self.assertTrue(source.is_open)
        
        source.close()
        self.assertFalse(source.is_open)
        self.mock_connection.close.assert_called_once()
        
        # Safe to call multiple times
        source.close()
        self.assertEqual(self.mock_connection.close.call_count, 1)

    def test_06_receive_message_success(self):
        mock_msg = MagicMock()
        mock_msg.get_type.return_value = 'HEARTBEAT'
        self.mock_connection.recv_match.return_value = mock_msg
        
        source = MAVLinkSource()
        source.connect()
        
        # Receive non-blocking by definition
        result = source.receive()
        self.assertEqual(result, mock_msg)
        self.mock_connection.recv_match.assert_called_once_with(blocking=False)

    def test_07_receive_no_message(self):
        # recv_match returns None when no message is available in non-blocking mode
        self.mock_connection.recv_match.return_value = None
        
        source = MAVLinkSource()
        source.connect()
        
        result = source.receive()
        self.assertIsNone(result)

    def test_08_receive_not_open_error(self):
        source = MAVLinkSource()
        with self.assertRaises(MAVLinkConnectionError):
            source.receive()

    def test_09_receive_connection_lost_error(self):
        self.mock_connection.recv_match.side_effect = Exception("Socket closed")
        
        source = MAVLinkSource()
        source.connect()
        
        with self.assertRaises(MAVLinkConnectionError):
            source.receive()
            
        # Ensure state reflects disconnection
        self.assertFalse(source.is_open)

    @patch('src.source.mavlink_source.mavutil', None)
    def test_10_pymavlink_missing(self):
        # Test behavior when pymavlink is not installed
        source = MAVLinkSource()
        with self.assertRaisesRegex(MAVLinkConnectionError, "pymavlink is not installed"):
            source.connect()

if __name__ == '__main__':
    unittest.main()
