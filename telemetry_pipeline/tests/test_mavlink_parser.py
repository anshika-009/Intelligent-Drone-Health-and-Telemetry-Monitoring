import unittest
from unittest.mock import MagicMock
from src.parser.mavlink_parser import MAVLinkParser, ParsedMAVLinkMessage

class _MockMsg:
    def __init__(self, msg_type, **kwargs):
        self._type = msg_type
        for k, v in kwargs.items():
            setattr(self, k, v)
    def get_type(self):
        return self._type

class TestMAVLinkParser(unittest.TestCase):
    def setUp(self):
        self.parser = MAVLinkParser()

    def _create_mock_msg(self, msg_type, **kwargs):
        return _MockMsg(msg_type, **kwargs)

    def test_01_global_position_int(self):
        msg = self._create_mock_msg('GLOBAL_POSITION_INT', lat=450000000, lon=-1200000000, relative_alt=100500, time_boot_ms=12345)
        parsed = self.parser.parse(msg)
        
        self.assertIsInstance(parsed, ParsedMAVLinkMessage)
        self.assertEqual(parsed.message_type, 'GLOBAL_POSITION_INT')
        self.assertEqual(parsed.fields['lat'], 450000000)
        self.assertEqual(parsed.fields['lon'], -1200000000)
        self.assertEqual(parsed.fields['relative_alt'], 100500)
        self.assertEqual(parsed.fields['time_boot_ms'], 12345)

    def test_02_sys_status(self):
        msg = self._create_mock_msg('SYS_STATUS', voltage_battery=11500, battery_remaining=85, current_battery=1500)
        parsed = self.parser.parse(msg)
        
        self.assertEqual(parsed.message_type, 'SYS_STATUS')
        self.assertEqual(parsed.fields['voltage_battery'], 11500)
        self.assertEqual(parsed.fields['battery_remaining'], 85)
        self.assertEqual(parsed.fields['current_battery'], 1500)

    def test_12_sys_status_missing_fields(self):
        msg = self._create_mock_msg('SYS_STATUS')
        parsed = self.parser.parse(msg)
        self.assertIsNone(parsed.fields['current_battery'])

    def test_03_vfr_hud(self):
        msg = self._create_mock_msg('VFR_HUD', heading=180, airspeed=15.0, groundspeed=14.5, climb=-1.2)
        parsed = self.parser.parse(msg)
        
        self.assertEqual(parsed.message_type, 'VFR_HUD')
        self.assertEqual(parsed.fields['heading'], 180)
        self.assertEqual(parsed.fields['airspeed'], 15.0)
        self.assertEqual(parsed.fields['groundspeed'], 14.5)
        self.assertEqual(parsed.fields['climb'], -1.2)

    def test_04_raw_imu(self):
        msg = self._create_mock_msg('RAW_IMU', xacc=100, yacc=-200, zacc=981, temperature=3850, time_usec=12345678)
        parsed = self.parser.parse(msg)
        
        self.assertEqual(parsed.message_type, 'RAW_IMU')
        self.assertEqual(parsed.fields['xacc'], 100)
        self.assertEqual(parsed.fields['yacc'], -200)
        self.assertEqual(parsed.fields['zacc'], 981)
        self.assertEqual(parsed.fields['temperature'], 3850)
        self.assertEqual(parsed.fields['time_usec'], 12345678)

    def test_05_gps_raw_int(self):
        msg = self._create_mock_msg('GPS_RAW_INT', fix_type=3, satellites_visible=12, time_usec=12345678)
        parsed = self.parser.parse(msg)
        
        self.assertEqual(parsed.message_type, 'GPS_RAW_INT')
        self.assertEqual(parsed.fields['fix_type'], 3)
        self.assertEqual(parsed.fields['satellites_visible'], 12)
        self.assertEqual(parsed.fields['time_usec'], 12345678)

    def test_06_radio_status(self):
        msg = self._create_mock_msg('RADIO_STATUS', rssi=190)
        parsed = self.parser.parse(msg)
        
        self.assertEqual(parsed.message_type, 'RADIO_STATUS')
        self.assertEqual(parsed.fields['rssi'], 190)

    def test_07_unsupported_message_returns_none(self):
        msg = self._create_mock_msg('COMMAND_ACK', command=511, result=0)
        parsed = self.parser.parse(msg)
        self.assertIsNone(parsed)

    def test_11_heartbeat_parsing(self):
        msg = self._create_mock_msg('HEARTBEAT', type=2, autopilot=3, base_mode=81, custom_mode=0, system_status=4)
        parsed = self.parser.parse(msg)
        
        self.assertEqual(parsed.message_type, 'HEARTBEAT')
        self.assertEqual(parsed.fields['type'], 2)
        self.assertEqual(parsed.fields['autopilot'], 3)
        self.assertEqual(parsed.fields['base_mode'], 81)
        self.assertEqual(parsed.fields['custom_mode'], 0)
        self.assertEqual(parsed.fields['system_status'], 4)

    def test_08_malformed_message_returns_none(self):
        parsed = self.parser.parse("not a message object")
        self.assertIsNone(parsed)
        
        msg_without_type = MagicMock()
        msg_without_type.get_type.side_effect = AttributeError("No type")
        self.assertIsNone(self.parser.parse(msg_without_type))

    def test_09_no_unit_conversion_or_rename(self):
        msg = self._create_mock_msg('SYS_STATUS', voltage_battery=11500)
        parsed = self.parser.parse(msg)
        
        self.assertIn('voltage_battery', parsed.fields)
        self.assertNotIn('battery_voltage', parsed.fields)
        self.assertEqual(parsed.fields['voltage_battery'], 11500)
        
    def test_10_missing_fields_safely_handled(self):
        msg = _MockMsg('VFR_HUD')
        parsed = self.parser.parse(msg)
        self.assertEqual(parsed.fields['heading'], None)

    def test_13_unexpected_exception_propagates(self):
        msg_with_runtime_error = MagicMock()
        msg_with_runtime_error.get_type.side_effect = RuntimeError("Memory corruption / DB offline")
        
        with self.assertRaises(RuntimeError):
            self.parser.parse(msg_with_runtime_error)

if __name__ == '__main__':
    unittest.main()
