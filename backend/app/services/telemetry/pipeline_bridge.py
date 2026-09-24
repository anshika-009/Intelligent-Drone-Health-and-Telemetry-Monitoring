"""
Telemetry Pipeline Bridge
-------------------------

The main FastAPI application owns ONE PipelineRunner.

This bridge only converts the already-running pipeline state
into the backend telemetry format.

IMPORTANT:

    Do NOT create another PipelineRunner here.

Otherwise two independent MAVLink consumers may read from
the same UDP stream.
"""

import sys
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
PIPELINE_ROOT = REPOSITORY_ROOT / "telemetry_pipeline"

if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
if str(PIPELINE_ROOT) not in sys.path:
    sys.path.insert(0, str(PIPELINE_ROOT))

from telemetry_pipeline.src.integration.backend_adapter import (
    adapt_to_backend,
)


# The PipelineRunner is injected by main.py.
_pipeline_runner = None


def set_pipeline_runner(runner: Any) -> None:
    """
    Registers the single PipelineRunner owned by FastAPI.
    """

    global _pipeline_runner

    _pipeline_runner = runner


def get_latest_telemetry() -> dict[str, Any]:
    """
    Returns the latest state from the shared telemetry pipeline.

    This function does NOT poll MAVLink.

    The background telemetry loop in main.py is responsible
    for polling the pipeline.
    """

    if _pipeline_runner is None:
        raise RuntimeError(
            "Telemetry pipeline has not been initialized."
        )

    state = _pipeline_runner.get_state()

    return adapt_to_backend(state)






# from pathlib import Path
# import sys

# PIPELINE_ROOT = Path(__file__).resolve().parents[4] / "telemetry_pipeline"

# if str(PIPELINE_ROOT) not in sys.path:
#     sys.path.insert(0, str(PIPELINE_ROOT))

# from src.orchestrator.pipeline_runner import PipelineRunner
# from src.integration.backend_adapter import adapt_to_backend


# _pipeline = PipelineRunner()


# def get_latest_telemetry():
#     """
#     Read one MAVLink message through the canonical telemetry pipeline
#     and convert the resulting VehicleState to the backend schema.
#     """
#     if not _pipeline.is_active:
#         _pipeline.start()

#     _pipeline.poll_once()
#     state = _pipeline.get_state()

#     return adapt_to_backend(state)
