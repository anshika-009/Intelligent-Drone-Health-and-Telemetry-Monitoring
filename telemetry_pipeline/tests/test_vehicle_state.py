import unittest
from datetime import datetime
from pydantic import ValidationError
from src.models.vehicle_state import VehicleState

class TestVehicleState(unittest.TestCase):
    def test_01_valid_complete_vehicle_state(self):
        state = VehicleState(
            drone_id="CUSTOM-01",
            flight_id="CUSTOM-FLT-01",
            timestamp=datetime.now(),
            source_timestamp_ms=123456,
            latitude=45.0,
            longitude=-120.0,
            altitude=100.5,
            heading=180.0,
            airspeed=15.0,
            ground_speed=14.5,
            vertical_speed=-1.2,
            flight_mode="GUIDED",
            battery_voltage=11.5,
            battery_percentage=85.5,
            gps_fix=True,
            gps_satellites=12,
            signal_strength=95.0,
            temperature=38.5,
            ax=0.1,
            ay=-0.2,
            az=9.8,
            vibration=0.05
        )
        self.assertEqual(state.drone_id, "CUSTOM-01")
        self.assertEqual(state.latitude, 45.0)

    def test_02_valid_partially_populated(self):
        state = VehicleState(
            timestamp=datetime.now(),
            latitude=34.0,
            longitude=-118.0
        )
        self.assertEqual(state.latitude, 34.0)
        self.assertIsNone(state.battery_voltage)

    def test_03_nullable_fields_accept_none(self):
        state = VehicleState(
            timestamp=datetime.now(),
            latitude=None,
            battery_percentage=None,
            gps_satellites=None
        )
        self.assertIsNone(state.latitude)
        self.assertIsNone(state.battery_percentage)
        self.assertIsNone(state.gps_satellites)

    def test_04_invalid_latitude_rejected(self):
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), latitude=91.0)
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), latitude=-91.0)

    def test_05_invalid_longitude_rejected(self):
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), longitude=181.0)
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), longitude=-181.0)

    def test_06_invalid_battery_percentage_rejected(self):
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), battery_percentage=101.0)
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), battery_percentage=-1.0)

    def test_07_invalid_signal_strength_rejected(self):
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), signal_strength=101.0)
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), signal_strength=-1.0)

    def test_08_negative_gps_satellites_rejected(self):
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), gps_satellites=-1)

    def test_09_invalid_imu_values_rejected(self):
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), ax=101.0)
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), ay=-101.0)
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), az=101.0)

    def test_10_invalid_heading_rejected(self):
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), heading=361.0)
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), heading=-1.0)

    def test_11_invalid_airspeed_rejected(self):
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), airspeed=-1.0)

    def test_12_invalid_ground_speed_rejected(self):
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), ground_speed=-1.0)

    def test_13_invalid_vertical_speed_rejected(self):
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), vertical_speed=101.0)
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), vertical_speed=-101.0)

    def test_14_invalid_battery_voltage_rejected(self):
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), battery_voltage=-1.0)
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), battery_voltage=51.0)

    def test_15_source_timestamp_ms_may_be_none(self):
        state = VehicleState(timestamp=datetime.now(), source_timestamp_ms=None)
        self.assertIsNone(state.source_timestamp_ms)

    def test_16_vibration_may_be_none(self):
        state = VehicleState(timestamp=datetime.now(), vibration=None)
        self.assertIsNone(state.vibration)

    def test_17_default_drone_id(self):
        state = VehicleState(timestamp=datetime.now())
        self.assertEqual(state.drone_id, "DRONE-01")

    def test_18_default_flight_id(self):
        state = VehicleState(timestamp=datetime.now())
        self.assertEqual(state.flight_id, "FLT-LIVE-01")

    def test_19_extra_fields_rejected(self):
        with self.assertRaises(ValidationError):
            VehicleState(
                timestamp=datetime.now(),
                unexpected_field="should fail"
            )

    def test_20_valid_battery_current(self):
        state = VehicleState(timestamp=datetime.now(), battery_current=15.5)
        self.assertEqual(state.battery_current, 15.5)

    def test_21_invalid_battery_current(self):
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), battery_current=1001.0)
        with self.assertRaises(ValidationError):
            VehicleState(timestamp=datetime.now(), battery_current=-1001.0)

if __name__ == '__main__':
    unittest.main()
