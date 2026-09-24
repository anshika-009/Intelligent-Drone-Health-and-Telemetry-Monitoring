import unittest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from src.models.vehicle_state import VehicleState


class TestPipelineBridge(unittest.TestCase):

    @patch(
        "backend.app.services.telemetry.pipeline_bridge.adapt_to_backend"
    )
    def test_telemetry_is_adapted_from_vehicle_state(
        self, mock_adapt
    ):
        state = VehicleState(
            timestamp=datetime.now(timezone.utc),
            latitude=25.4921,
            longitude=81.8639,
            altitude=20.5,
            battery_voltage=12.4,
            ax=1.2,
            ay=-0.8,
            az=9.7,
        )

        mock_runner = Mock()
        mock_runner.get_state.return_value = state

        mock_adapt.return_value = {
            "latitude": 25.4921,
            "longitude": 81.8639,
            "altitude": 20.5,
            "battery_voltage": 12.4,
            "ax": 1.2,
            "ay": -0.8,
            "az": 9.7,
        }

        from backend.app.services.telemetry.pipeline_bridge import (
            set_pipeline_runner,
            get_latest_telemetry,
        )

        set_pipeline_runner(mock_runner)

        result = get_latest_telemetry()

        self.assertEqual(result["latitude"], 25.4921)
        self.assertEqual(result["longitude"], 81.8639)
        self.assertEqual(result["altitude"], 20.5)
        self.assertEqual(result["battery_voltage"], 12.4)
        self.assertEqual(result["ax"], 1.2)
        self.assertEqual(result["ay"], -0.8)
        self.assertEqual(result["az"], 9.7)

        mock_runner.get_state.assert_called_once()
        mock_adapt.assert_called_once_with(state)

    def test_pipeline_must_be_initialized(self):
        from backend.app.services.telemetry.pipeline_bridge import (
            set_pipeline_runner,
            get_latest_telemetry,
        )

        set_pipeline_runner(None)

        with self.assertRaises(RuntimeError):
            get_latest_telemetry()


if __name__ == "__main__":
    unittest.main()
