from pathlib import Path
import sys

PIPELINE_ROOT = Path(__file__).resolve().parents[4] / "telemetry_pipeline"

if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from src.orchestrator.pipeline_runner import PipelineRunner
from src.integration.backend_adapter import adapt_to_backend


_pipeline = PipelineRunner()


def get_latest_telemetry():
    """
    Read one MAVLink message through the canonical telemetry pipeline
    and convert the resulting VehicleState to the backend schema.
    """
    if not _pipeline.is_active:
        _pipeline.start()

    _pipeline.poll_once()
    state = _pipeline.get_state()

    return adapt_to_backend(state)
