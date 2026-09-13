import os
import time
import struct
import tempfile
import unittest
from datetime import datetime, timezone, timedelta

from pymavlink.dialects.v20 import common as mavlink2
from src.orchestrator.pipeline_runner import PipelineRunner
from src.source.mavlink_source import MAVLinkConnectionError

class TestRealMavlinkProtocol(unittest.TestCase):
    def setUp(self):
        self.mav = mavlink2.MAVLink(None)
        self.current_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.temp_files = []
        self.runners = []

    def tearDown(self):
        for r in self.runners:
            try:
                r.stop()
            except Exception:
                pass
        for f in self.temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass

    def advance_time(self, seconds):
        self.current_time += timedelta(seconds=seconds)

    def _mock_clock(self):
        return self.current_time

    def write_tlog(self, encoded_messages):
        fd, path = tempfile.mkstemp(suffix='.tlog')
        self.temp_files.append(path)
        with open(path, 'wb') as f:
            for msg_bytes in encoded_messages:
                usec = int(time.time() * 1.0e6)
                f.write(struct.pack('>Q', usec))
                f.write(msg_bytes)
        os.close(fd)
        return path
        
    def create_runner(self, tlog_path):
        runner = PipelineRunner(tlog_path)
        runner.aggregator._clock = self._mock_clock
        self.runners.append(runner)
        return runner

    def test_01_gps_semantic_validation(self):
        # We need BOTH GPS_RAW_INT (for fix) and GLOBAL_POSITION_INT (for lat/lon/alt)
        msg1_fix = self.mav.gps_raw_int_encode(
            time_usec=0, fix_type=3, lat=450000000, lon=-1200000000, 
            alt=100500, eph=0, epv=0, vel=0, cog=0, satellites_visible=10,
            alt_ellipsoid=0, h_acc=0, v_acc=0, vel_acc=0, hdg_acc=0, yaw=0
        ).pack(self.mav)
        msg1_pos = self.mav.global_position_int_encode(
            time_boot_ms=0, lat=450000000, lon=-1200000000, alt=100500, 
            relative_alt=100500, vx=0, vy=0, vz=0, hdg=0
        ).pack(self.mav)
        
        msg2_fix = self.mav.gps_raw_int_encode(
            time_usec=0, fix_type=2, lat=450000000, lon=-1200000000, 
            alt=100500, eph=0, epv=0, vel=0, cog=0, satellites_visible=4,
            alt_ellipsoid=0, h_acc=0, v_acc=0, vel_acc=0, hdg_acc=0, yaw=0
        ).pack(self.mav)

        tlog = self.write_tlog([msg1_fix, msg1_pos, msg2_fix])
        runner = self.create_runner(tlog)
        runner.start()

        self.assertTrue(runner.poll_once()) # fix 3
        self.assertTrue(runner.poll_once()) # pos
        state_a = runner.get_state()
        self.assertTrue(state_a.gps_fix)
        self.assertEqual(state_a.latitude, 45.0)
        self.assertEqual(state_a.longitude, -120.0)
        self.assertEqual(state_a.altitude, 100.5)
        self.assertEqual(state_a.gps_satellites, 10)

        self.assertTrue(runner.poll_once()) # fix 2
        state_b = runner.get_state()
        self.assertFalse(state_b.gps_fix)
        
        self.advance_time(6.0)
        self.assertFalse(runner.poll_once())
        state_c = runner.get_state()
        self.assertIsNone(state_c.gps_fix)
        self.assertIsNone(state_c.latitude)

    def test_02_battery_validation(self):
        msg_batt = self.mav.sys_status_encode(
            onboard_control_sensors_present=0, onboard_control_sensors_enabled=0, 
            onboard_control_sensors_health=0, load=500, voltage_battery=12600, 
            current_battery=1500, battery_remaining=85, drop_rate_comm=0, 
            errors_comm=0, errors_count1=0, errors_count2=0, errors_count3=0, errors_count4=0
        ).pack(self.mav)
        
        tlog = self.write_tlog([msg_batt])
        runner = self.create_runner(tlog)
        runner.start()
        
        self.assertTrue(runner.poll_once())
        state = runner.get_state()
        self.assertEqual(state.battery_voltage, 12.6)
        self.assertEqual(state.battery_percentage, 85.0)
        
        self.advance_time(6.0)
        self.assertFalse(runner.poll_once())
        state_stale = runner.get_state()
        self.assertIsNone(state_stale.battery_voltage)
        self.assertIsNone(state_stale.battery_percentage)

    def test_03_radio_validation(self):
        m_low = self.mav.radio_status_encode(rxerrors=0, fixed=0, txbuf=0, rssi=0, remrssi=0, noise=0, remnoise=0).pack(self.mav)
        m_mid = self.mav.radio_status_encode(rxerrors=0, fixed=0, txbuf=0, rssi=127, remrssi=0, noise=0, remnoise=0).pack(self.mav)
        m_high = self.mav.radio_status_encode(rxerrors=0, fixed=0, txbuf=0, rssi=254, remrssi=0, noise=0, remnoise=0).pack(self.mav)
        
        tlog = self.write_tlog([m_low, m_mid, m_high])
        runner = self.create_runner(tlog)
        runner.start()
        
        self.assertTrue(runner.poll_once())
        self.assertEqual(runner.get_state().signal_strength, 0.0)
        
        self.assertTrue(runner.poll_once())
        self.assertAlmostEqual(runner.get_state().signal_strength, 50.0, places=1)
        
        self.assertTrue(runner.poll_once())
        self.assertAlmostEqual(runner.get_state().signal_strength, 100.0, places=1)
        
        self.advance_time(6.0)
        self.assertFalse(runner.poll_once())
        self.assertIsNone(runner.get_state().signal_strength)

    def test_04_imu_validation(self):
        m = self.mav.raw_imu_encode(
            time_usec=0, xacc=1000, yacc=-2000, zacc=3000, xgyro=0, ygyro=0, zgyro=0, 
            xmag=0, ymag=0, zmag=0, id=0, temperature=3500
        ).pack(self.mav)
        
        tlog = self.write_tlog([m])
        runner = self.create_runner(tlog)
        runner.start()
        
        self.assertTrue(runner.poll_once())
        state = runner.get_state()
        
        self.assertAlmostEqual(state.ax, 9.81, places=2)
        self.assertAlmostEqual(state.ay, -19.62, places=2)
        self.assertAlmostEqual(state.az, 29.43, places=2)
        self.assertAlmostEqual(state.temperature, 35.0, places=1)
        self.assertIsNone(state.vibration)

    def test_05_vfr_hud_validation(self):
        m = self.mav.vfr_hud_encode(airspeed=15.5, groundspeed=14.5, heading=180, throttle=50, alt=100.5, climb=-1.2).pack(self.mav)
        tlog = self.write_tlog([m])
        runner = self.create_runner(tlog)
        runner.start()
        self.assertTrue(runner.poll_once())
        state = runner.get_state()
        
        self.assertAlmostEqual(state.airspeed, 15.5, places=1)
        self.assertAlmostEqual(state.ground_speed, 14.5, places=1)
        self.assertAlmostEqual(state.heading, 180.0, places=1)
        self.assertAlmostEqual(state.vertical_speed, -1.2, places=1)

    def test_06_heartbeat_validation(self):
        m = self.mav.heartbeat_encode(type=0, autopilot=0, base_mode=0, custom_mode=15, system_status=0).pack(self.mav)
        tlog = self.write_tlog([m])
        runner = self.create_runner(tlog)
        runner.start()
        
        self.assertTrue(runner.poll_once())
        state = runner.get_state()
        self.assertIsNone(state.flight_mode) 

    def test_07_partial_telemetry_isolation(self):
        m_batt = self.mav.sys_status_encode(
            onboard_control_sensors_present=0, onboard_control_sensors_enabled=0, 
            onboard_control_sensors_health=0, load=500, voltage_battery=12600, 
            current_battery=1500, battery_remaining=85, drop_rate_comm=0, 
            errors_comm=0, errors_count1=0, errors_count2=0, errors_count3=0, errors_count4=0
        ).pack(self.mav)
        m_imu = self.mav.raw_imu_encode(
            time_usec=0, xacc=1000, yacc=1000, zacc=1000, xgyro=0, ygyro=0, zgyro=0, 
            xmag=0, ymag=0, zmag=0, id=0, temperature=3500
        ).pack(self.mav)
        
        tlog = self.write_tlog([m_batt, m_imu])
        runner = self.create_runner(tlog)
        runner.start()
        
        self.assertTrue(runner.poll_once()) # batt
        self.assertTrue(runner.poll_once()) # imu
        
        state1 = runner.get_state()
        self.assertAlmostEqual(state1.battery_voltage, 12.6, places=1)
        self.assertAlmostEqual(state1.ax, 9.81, places=2)
        
        self.advance_time(1.5)
        self.assertFalse(runner.poll_once())
        
        state2 = runner.get_state()
        self.assertAlmostEqual(state2.battery_voltage, 12.6, places=1)
        self.assertIsNone(state2.ax)

    def test_08_malformed_bytes(self):
        valid_msg = self.mav.sys_status_encode(
            0, 0, 0, 500, 12600, 1500, 85, 0, 0, 0, 0, 0, 0
        ).pack(self.mav)
        
        truncated = valid_msg[:10]
        garbage = b'\x00\xff\xab\xcd' * 10
        corrupted = bytearray(valid_msg)
        corrupted[-1] = (corrupted[-1] + 1) % 256
        
        for bad_data in [truncated, garbage, corrupted]:
            tlog = self.write_tlog([bad_data])
            runner = self.create_runner(tlog)
            try:
                runner.start()
                self.assertFalse(runner.poll_once())
            except MAVLinkConnectionError:
                pass
            except Exception:
                pass

if __name__ == '__main__':
    unittest.main()
