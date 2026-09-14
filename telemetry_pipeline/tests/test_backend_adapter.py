import unittest
from datetime import datetime, timezone
from copy import deepcopy

from src.models.vehicle_state import VehicleState
from src.integration.backend_adapter import adapt_to_backend

class TestBackendAdapter(unittest.TestCase):
    
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.populated_state = VehicleState(
            drone_id="TEST-DRONE",
            flight_id="TEST-FLIGHT",
            timestamp=self.now,
            latitude=12.9716,
            longitude=77.5946,
            altitude=150.5,
            ground_speed=12.2,
            airspeed=13.0,
            vertical_speed=-1.5,
            heading=45.0,
            battery_percentage=85.5,
            battery_voltage=11.4,
            temperature=45.2,
            signal_strength=92.0,
            gps_fix=True,
            gps_satellites=12,
            ax=1.2,
            ay=-0.8,
            az=9.7
        )
        
        self.empty_state = VehicleState(
            drone_id="DRONE-01",
            flight_id="FLT-01",
            timestamp=self.now
        )

    def test_01_fully_populated_state(self):
        output = adapt_to_backend(self.populated_state)
        
        self.assertEqual(output['drone_id'], "TEST-DRONE")
        self.assertEqual(output['latitude'], 12.9716)
        self.assertEqual(output['battery_percentage'], 85.5)
        self.assertEqual(output['gps_fix'], True)
        self.assertEqual(output['gps_satellites'], 12)

    def test_02_empty_state_fallbacks(self):
        output = adapt_to_backend(self.empty_state)
        
        self.assertIsNone(output['latitude'])
        self.assertIsNone(output['longitude'])
        self.assertIsNone(output['battery_voltage'])
        self.assertIsNone(output['signal_strength'])
        self.assertIsNone(output['gps_fix'])
        self.assertIsNone(output['gps_satellites'])

    def test_03_voltage_alias(self):
        output = adapt_to_backend(self.populated_state)
        self.assertEqual(output['battery_voltage'], 11.4)
        self.assertEqual(output['voltage'], 11.4)

    def test_04_timestamp_isoformat(self):
        output = adapt_to_backend(self.populated_state)
        self.assertEqual(output['timestamp'], self.now.isoformat())

    def test_05_compatibility_placeholders(self):
        output = adapt_to_backend(self.populated_state)
        
        self.assertEqual(output['vibration'], 0.0)
        self.assertEqual(output['motor_outputs'], [0, 0, 0, 0])
        self.assertEqual(output['estimated_remaining_flight_time'], 20.0)
        self.assertEqual(output['flight_mode'], "UNKNOWN")

    def test_06_health_boundary(self):
        output = adapt_to_backend(self.populated_state)
        self.assertNotIn("health_score", output)

    def test_07_no_mutation(self):
        original_dict = self.populated_state.model_dump()
        adapt_to_backend(self.populated_state)
        self.assertEqual(self.populated_state.model_dump(), original_dict)

    def test_08_statelessness(self):
        out1 = adapt_to_backend(self.populated_state)
        out2 = adapt_to_backend(self.empty_state)
        
        self.assertEqual(out1['battery_voltage'], 11.4)
        self.assertIsNone(out2['battery_voltage'])

    def test_09_imu_acceleration_mapping(self):
        output = adapt_to_backend(self.populated_state)

        self.assertEqual(output["ax"], 1.2)
        self.assertEqual(output["ay"], -0.8)
        self.assertEqual(output["az"], 9.7)

    def test_10_none_values_are_preserved(self):
        state = VehicleState(
            timestamp=datetime.now(timezone.utc)
        )

        output = adapt_to_backend(state)

        self.assertIsNone(output["latitude"])
        self.assertIsNone(output["longitude"])
        self.assertIsNone(output["altitude"])
        self.assertIsNone(output["ground_speed"])
        self.assertIsNone(output["airspeed"])
        self.assertIsNone(output["vertical_speed"])
        self.assertIsNone(output["heading"])
        self.assertIsNone(output["battery_percentage"])
        self.assertIsNone(output["battery_voltage"])
        self.assertIsNone(output["temperature"])
        self.assertIsNone(output["signal_strength"])
        self.assertIsNone(output["gps_fix"])
        self.assertIsNone(output["gps_satellites"])
        self.assertIsNone(output["ax"])
        self.assertIsNone(output["ay"])
        self.assertIsNone(output["az"])

if __name__ == '__main__':
    unittest.main()
