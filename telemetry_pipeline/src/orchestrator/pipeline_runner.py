from typing import Optional

from src.source.mavlink_source import MAVLinkSource
from src.parser.mavlink_parser import MAVLinkParser
from src.normalizer.mavlink_normalizer import MAVLinkNormalizer
from src.aggregator.state_aggregator import StateAggregator
from src.models.vehicle_state import VehicleState

class PipelineNotActiveError(Exception):
    """Exception raised when lifecycle semantics are violated."""
    pass

class PipelineRunner:
    """
    The single orchestration facade for the Embedded/Data Pipeline.
    Composes the MAVLink layers synchronously.
    """
    def __init__(self, connection_string: Optional[str] = None):
        self.source = MAVLinkSource(connection_string=connection_string)
        self.parser = MAVLinkParser()
        self.normalizer = MAVLinkNormalizer()
        self.aggregator = StateAggregator()

    def start(self) -> None:
        """Connects the underlying MAVLink source idempotently."""
        if not self.is_active:
            self.source.connect()

    def stop(self) -> None:
        """Closes the underlying MAVLink source idempotently."""
        if self.is_active:
            self.source.close()

    @property
    def is_active(self) -> bool:
        """Returns True if the transport source is open."""
        return self.source.is_open

    def poll_once(self) -> bool:
        """
        Performs exactly one non-blocking polling cycle.
        Returns True if a message was successfully processed and aggregated.
        Returns False if no usable message was processed.
        Transport exceptions are allowed to propagate.
        Raises PipelineNotActiveError if called before start() or after stop().
        """
        if not self.is_active:
            raise PipelineNotActiveError("Cannot poll: Pipeline runner is not active.")

        message = self.source.receive()
        if message is None:
            return False

        return self._process_message(message)

    def poll_available(self, max_messages: int = 256) -> bool:
        """Process all currently queued messages up to a bounded limit."""
        if not self.is_active:
            raise PipelineNotActiveError("Cannot poll: Pipeline runner is not active.")

        processed = False
        for _ in range(max_messages):
            message = self.source.receive()
            if message is None:
                break
            processed = self._process_message(message) or processed
        return processed

    def _process_message(self, message) -> bool:
        """Parse, normalize, and aggregate one raw MAVLink message."""

        parsed = self.parser.parse(message)
        if parsed is None:
            return False

        normalized = self.normalizer.normalize(parsed)
        if not normalized:  # Catches None or empty {}
            return False

        self.aggregator.update(normalized)
        return True

    def get_state(self) -> VehicleState:
        """Produces the aggregated canonical VehicleState."""
        return self.aggregator.get_state()
