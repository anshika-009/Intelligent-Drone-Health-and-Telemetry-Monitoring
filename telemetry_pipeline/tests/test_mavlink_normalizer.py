import unittest
from src.parser.mavlink_parser import ParsedMAVLinkMessage
from src.normalizer.mavlink_normalizer import MAVLinkNormalizer

class TestMAVLinkNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = MAVLinkNormalizer()

    def test_01_global_position_int_conversion(self):
        msg = ParsedMAVLinkMessage(
            message_type='GLOBAL_POSITION_INT',
            fields={'lat': 450000000, 'lon': -1200000000, 'relative_alt': 100500, 'time_boot_ms': 12345}
        )
        res = self.normalizer.normalize(msg)
        self.assertAlmostEqual(res['latitude'], 45.0)
        self.assertAlmostEqual(res['longitude'], -120.0)
        self.assertAlmostEqual(res['altitude'], 100.5)
        self.assertEqual(res['source_timestamp_ms'], 12345)
        
        # Test 16: Uses canonical IDHTM names
        self.assertNotIn('lat', res)
        self.assertNotIn('lon', res)
        self.assertNotIn('relative_alt', res)
        self.assertNotIn('time_boot_ms', res)

    def test_02_sys_status_voltage_conversion(self):
        msg = ParsedMAVLinkMessage(
            message_type='SYS_STATUS',
            fields={'voltage_battery': 11500, 'battery_remaining': 85}
        )
        res = self.normalizer.normalize(msg)
        self.assertAlmostEqual(res['battery_voltage'], 11.5)
        self.assertAlmostEqual(res['battery_percentage'], 85.0)
        self.assertNotIn('voltage_battery', res)

    def test_03_sys_status_battery_remaining_none(self):
        msg = ParsedMAVLinkMessage(
            message_type='SYS_STATUS',
            fields={'voltage_battery': 11500, 'battery_remaining': -1}
        )
        res = self.normalizer.normalize(msg)
        self.assertIsNone(res['battery_percentage'])

    def test_04_vfr_hud_renaming(self):
        msg = ParsedMAVLinkMessage(
            message_type='VFR_HUD',
            fields={'heading': 180, 'airspeed': 15.0, 'groundspeed': 14.5, 'climb': -1.2}
        )
        res = self.normalizer.normalize(msg)
        self.assertEqual(res['heading'], 180.0)
        self.assertEqual(res['airspeed'], 15.0)
        self.assertEqual(res['ground_speed'], 14.5)
        self.assertEqual(res['vertical_speed'], -1.2)
        
        self.assertNotIn('groundspeed', res)
        self.assertNotIn('climb', res)

    def test_05_raw_imu_acceleration_conversion(self):
        msg = ParsedMAVLinkMessage(
            message_type='RAW_IMU',
            fields={'xacc': 1000, 'yacc': -2000, 'zacc': 981, 'temperature': 3850}
        )
        res = self.normalizer.normalize(msg)
        self.assertAlmostEqual(res['ax'], 1000 * 0.00981)
        self.assertAlmostEqual(res['ay'], -2000 * 0.00981)
        self.assertAlmostEqual(res['az'], 981 * 0.00981)

    def test_06_raw_imu_temperature_conversion(self):
        msg = ParsedMAVLinkMessage(
            message_type='RAW_IMU',
            fields={'temperature': 3850}
        )
        res = self.normalizer.normalize(msg)
        self.assertAlmostEqual(res['temperature'], 38.5)

    def test_07_raw_imu_temperature_zero_to_none(self):
        msg = ParsedMAVLinkMessage(
            message_type='RAW_IMU',
            fields={'temperature': 0}
        )
        res = self.normalizer.normalize(msg)
        self.assertIsNone(res['temperature'])

    def test_08_gps_fix_type_ge_3(self):
        msg = ParsedMAVLinkMessage(message_type='GPS_RAW_INT', fields={'fix_type': 3})
        res = self.normalizer.normalize(msg)
        self.assertTrue(res['gps_fix'])
        
        msg2 = ParsedMAVLinkMessage(message_type='GPS_RAW_INT', fields={'fix_type': 6})
        res2 = self.normalizer.normalize(msg2)
        self.assertTrue(res2['gps_fix'])

    def test_09_gps_fix_type_lt_3(self):
        msg = ParsedMAVLinkMessage(message_type='GPS_RAW_INT', fields={'fix_type': 2})
        res = self.normalizer.normalize(msg)
        self.assertFalse(res['gps_fix'])
        
        msg2 = ParsedMAVLinkMessage(message_type='GPS_RAW_INT', fields={'fix_type': 0})
        res2 = self.normalizer.normalize(msg2)
        self.assertFalse(res2['gps_fix'])

    def test_10_gps_satellites_visible_255(self):
        msg = ParsedMAVLinkMessage(message_type='GPS_RAW_INT', fields={'satellites_visible': 255})
        res = self.normalizer.normalize(msg)
        self.assertIsNone(res['gps_satellites'])
        
        msg2 = ParsedMAVLinkMessage(message_type='GPS_RAW_INT', fields={'satellites_visible': 12})
        res2 = self.normalizer.normalize(msg2)
        self.assertEqual(res2['gps_satellites'], 12)

    def test_11_radio_status_rssi_255(self):
        msg = ParsedMAVLinkMessage(message_type='RADIO_STATUS', fields={'rssi': 255})
        res = self.normalizer.normalize(msg)
        self.assertIsNone(res['signal_strength'])

    def test_12_radio_status_provisional_mapping(self):
        msg = ParsedMAVLinkMessage(message_type='RADIO_STATUS', fields={'rssi': 127})
        res = self.normalizer.normalize(msg)
        expected = (127 / 254.0) * 100.0
        self.assertAlmostEqual(res['signal_strength'], expected)
        
        # Test clamping if somehow > 254 but not 255
        msg_clamp = ParsedMAVLinkMessage(message_type='RADIO_STATUS', fields={'rssi': 260})
        res_clamp = self.normalizer.normalize(msg_clamp)
        self.assertAlmostEqual(res_clamp['signal_strength'], 100.0)

    def test_13_unsupported_message_type(self):
        msg = ParsedMAVLinkMessage(message_type='COMMAND_ACK', fields={'command': 511})
        res = self.normalizer.normalize(msg)
        self.assertIsNone(res)
        
    def test_14_missing_fields_handled_safely(self):
        msg = ParsedMAVLinkMessage(message_type='GLOBAL_POSITION_INT', fields={'lat': 450000000}) # Missing lon/alt
        res = self.normalizer.normalize(msg)
        self.assertIn('latitude', res)
        self.assertNotIn('longitude', res)
        self.assertNotIn('altitude', res)

    def test_15_no_aggregation(self):
        # A single message should only produce its own fields
        msg = ParsedMAVLinkMessage(message_type='SYS_STATUS', fields={'voltage_battery': 11500})
        res = self.normalizer.normalize(msg)
        self.assertIn('battery_voltage', res)
        self.assertNotIn('latitude', res)
        self.assertNotIn('drone_id', res)

    def test_16_heartbeat_is_handled(self):
        msg = ParsedMAVLinkMessage(message_type='HEARTBEAT', fields={'type': 2, 'autopilot': 3, 'base_mode': 81, 'custom_mode': 0, 'system_status': 4})
        res = self.normalizer.normalize(msg)
        # It should handle it without inventing flight_mode
        self.assertNotIn('flight_mode', res)
        self.assertEqual(res['vehicle_type'], 2)
        self.assertEqual(res['autopilot'], 3)
        self.assertEqual(res['base_mode'], 81)
        self.assertEqual(res['custom_mode'], 0)
        self.assertEqual(res['system_status'], 4)

    def test_17_sys_status_battery_current(self):
        msg = ParsedMAVLinkMessage(message_type='SYS_STATUS', fields={'current_battery': 1500})
        res = self.normalizer.normalize(msg)
        self.assertAlmostEqual(res['battery_current'], 15.0)

    def test_18_sys_status_battery_current_none(self):
        msg = ParsedMAVLinkMessage(message_type='SYS_STATUS', fields={'current_battery': -1})
        res = self.normalizer.normalize(msg)
        self.assertIsNone(res['battery_current'])

if __name__ == '__main__':
    unittest.main()
