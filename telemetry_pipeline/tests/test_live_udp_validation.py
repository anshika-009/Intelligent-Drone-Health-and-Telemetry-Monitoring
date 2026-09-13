import unittest
import time
import socket
from datetime import datetime, timezone, timedelta
from pymavlink.dialects.v20 import common as mavlink2
from pymavlink import mavutil
from src.orchestrator.pipeline_runner import PipelineRunner

class LiveUDPProducer:
    def __init__(self, port=14550):
        self.port = port
        self.conn = mavutil.mavlink_connection(f'udpout:127.0.0.1:{port}', source_system=1, source_component=1)
        
    def send_gps(self):
        self.conn.mav.gps_raw_int_send(time_usec=0, fix_type=3, lat=450000000, lon=-1200000000, alt=100500, eph=0, epv=0, vel=0, cog=0, satellites_visible=10)
        self.conn.mav.global_position_int_send(time_boot_ms=0, lat=450000000, lon=-1200000000, alt=100500, relative_alt=100500, vx=0, vy=0, vz=0, hdg=0)
        
    def send_imu(self):
        self.conn.mav.raw_imu_send(time_usec=0, xacc=1000, yacc=-2000, zacc=3000, xgyro=0, ygyro=0, zgyro=0, xmag=0, ymag=0, zmag=0)
        
    def send_battery(self):
        self.conn.mav.sys_status_send(onboard_control_sensors_present=0, onboard_control_sensors_enabled=0, onboard_control_sensors_health=0, load=500, voltage_battery=12600, current_battery=1500, battery_remaining=85, drop_rate_comm=0, errors_comm=0, errors_count1=0, errors_count2=0, errors_count3=0, errors_count4=0)

    def send_heartbeat(self):
        self.conn.mav.heartbeat_send(type=mavlink2.MAV_TYPE_QUADROTOR, autopilot=mavlink2.MAV_AUTOPILOT_ARDUPILOTMEGA, base_mode=0, custom_mode=0, system_status=mavlink2.MAV_STATE_ACTIVE)

    def send_radio(self):
        self.conn.mav.radio_status_send(rxerrors=0, fixed=0, txbuf=0, rssi=127, remrssi=0, noise=0, remnoise=0)

    def send_vfr(self):
        self.conn.mav.vfr_hud_send(airspeed=15.5, groundspeed=14.5, heading=180, throttle=50, alt=100.5, climb=-1.2)

    def send_garbage(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(b'\x00\xff\xab\xcd' * 10, ('127.0.0.1', self.port))
        sock.close()

    def close(self):
        self.conn.close()

class TestLiveUDPValidation(unittest.TestCase):
    def setUp(self):
        self.port = 14555 
        self.runner = PipelineRunner(f'udpin:127.0.0.1:{self.port}')
        self.current_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        self.runner.aggregator._clock = self._mock_clock
        self.producer = LiveUDPProducer(self.port)
        self.runner.start()
        time.sleep(0.1)

    def tearDown(self):
        self.producer.close()
        self.runner.stop()

    def _mock_clock(self):
        return self.current_time

    def advance_time(self, seconds):
        self.current_time += timedelta(seconds=seconds)

    def _drain_messages(self):
        count = 0
        while self.runner.poll_once():
            count += 1
        return count

    def test_A_C_continuous_reception_and_normalization(self):
        for _ in range(5):
            self.producer.send_gps()
            self.producer.send_battery()
            self.producer.send_imu()
            time.sleep(0.01)
            
        processed = self._drain_messages()
        self.assertGreater(processed, 0, "Must have processed live messages")
        state = self.runner.get_state()
        self.assertEqual(state.latitude, 45.0) 
        self.assertEqual(state.battery_voltage, 12.6)
        self.assertAlmostEqual(state.ax, 9.81, places=2)

    def test_D_heartbeat_and_radio_live(self):
        self.producer.send_heartbeat()
        self.producer.send_radio()
        time.sleep(0.01)
        self._drain_messages()
        
        state = self.runner.get_state()
        self.assertEqual(self.runner.aggregator.metadata.get('vehicle_type'), mavlink2.MAV_TYPE_QUADROTOR)
        self.assertEqual(state.signal_strength, 50.0)

    def test_B_partial_telemetry(self):
        self.producer.send_gps()
        time.sleep(0.01)
        self._drain_messages()
        state = self.runner.get_state()
        self.assertEqual(state.latitude, 45.0)
        self.assertIsNone(state.battery_voltage)
        
        self.producer.send_battery()
        time.sleep(0.01)
        self._drain_messages()
        state = self.runner.get_state()
        self.assertEqual(state.latitude, 45.0)
        self.assertEqual(state.battery_voltage, 12.6)

    def test_E_deterministic_clock_ttl_staleness(self):
        self.producer.send_gps()
        self.producer.send_imu()
        time.sleep(0.01)
        self._drain_messages()
        
        self.assertIsNotNone(self.runner.get_state().ax)
        self.assertIsNotNone(self.runner.get_state().latitude)
        
        self.advance_time(1.5)
        self.producer.send_gps() 
        time.sleep(0.01)
        self._drain_messages()
        
        self.assertIsNone(self.runner.get_state().ax, "IMU should decay to None")
        self.assertIsNotNone(self.runner.get_state().latitude, "GPS should remain fresh")

    def test_F_intentional_packet_loss(self):
        self.producer.send_gps()
        self.producer.send_battery()
        self.producer.send_imu()
        time.sleep(0.01)
        self._drain_messages()
        self.assertEqual(self.runner.get_state().battery_voltage, 12.6)
        
        self.advance_time(6.0) 
        
        self.producer.send_gps()
        self.producer.send_imu()
        time.sleep(0.01)
        self._drain_messages()
        
        state = self.runner.get_state()
        self.assertIsNone(state.battery_voltage, "Omitted telemetry should decay")
        self.assertEqual(state.latitude, 45.0)
        self.assertAlmostEqual(state.ax, 9.81, places=2)

    def test_G_bursts(self):
        for _ in range(100):
            self.producer.send_vfr()
        time.sleep(0.1)
        processed = self._drain_messages()
        self.assertGreater(processed, 50)
        self.assertEqual(self.runner.get_state().airspeed, 15.5)

    def test_H_malformed_traffic(self):
        self.producer.send_battery() 
        time.sleep(0.01)
        self._drain_messages()
        
        self.producer.send_garbage()
        time.sleep(0.01)
        self._drain_messages() 
        
        for _ in range(5):
            self.producer.send_gps()
            time.sleep(0.01)
            
        self._drain_messages()
        state = self.runner.get_state()
        self.assertEqual(state.battery_voltage, 12.6, "Unrelated state remains")
        self.assertEqual(state.latitude, 45.0, "Subsequent valid message processed")

    def test_I_producer_interruption_and_reappearance(self):
        self.producer.send_battery()
        time.sleep(0.01)
        self._drain_messages()
        
        self.producer.close()
        
        self.advance_time(10)
        self._drain_messages()
        self.assertIsNone(self.runner.get_state().battery_voltage)
        
        self.producer = LiveUDPProducer(self.port)
        self.producer.send_battery()
        time.sleep(0.01)
        self._drain_messages()
        
        self.assertEqual(self.runner.get_state().battery_voltage, 12.6)

    def test_J_shutdown(self):
        self.assertTrue(self.runner.source._master is not None)
        self.runner.stop()
        self.assertTrue(self.runner.source._master is None)

if __name__ == '__main__':
    unittest.main()

