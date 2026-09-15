import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from src.models.vehicle_state import VehicleState

class TestPipelineBridge(unittest.TestCase):

    @patch("backend.app.services.telemetry.pipeline_bridge._pipeline")
    def test_telemetry_is_adapted_from_vehicle_state(self, mock_pipeline):
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

        mock_pipeline.is_active = True
        mock_pipeline.poll_once.return_value = True
        mock_pipeline.get_state.return_value = state

        from backend.app.services.telemetry.pipeline_bridge import (
            get_latest_telemetry,
        )

        result = get_latest_telemetry()

        self.assertEqual(result["latitude"], 25.4921)
        self.assertEqual(result["longitude"], 81.8639)
        self.assertEqual(result["altitude"], 20.5)

        self.assertEqual(result["battery_voltage"], 12.4)

        self.assertEqual(result["ax"], 1.2)
        self.assertEqual(result["ay"], -0.8)
        self.assertEqual(result["az"], 9.7)

        mock_pipeline.poll_once.assert_called_once()
        mock_pipeline.get_state.assert_called_once()

    @patch("backend.app.services.telemetry.pipeline_bridge._pipeline")
    def test_pipeline_is_started_when_inactive(self, mock_pipeline):
        state = VehicleState(
            timestamp=datetime.now(timezone.utc),
        )

        mock_pipeline.is_active = False
        mock_pipeline.get_state.return_value = state

        from backend.app.services.telemetry.pipeline_bridge import (
            get_latest_telemetry,
        )

        get_latest_telemetry()

        mock_pipeline.start.assert_called_once()
        mock_pipeline.poll_once.assert_called_once()


if __name__ == "__main__":
    unittest.main()
