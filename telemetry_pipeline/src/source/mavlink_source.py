import os
from typing import Any, Optional

try:
    from pymavlink import mavutil
except ImportError:
    mavutil = None  # Graceful fallback for test environments without pymavlink

class MAVLinkConnectionError(Exception):
    """Exception raised for MAVLink connection and receive errors."""
    pass

class MAVLinkSource:
    """
    Manages the MAVLink connection (UDP/Serial) and raw message acquisition.
    This component handles only the network/serial I/O.
    It does not perform normalization, state aggregation, or routing.
    """
    def __init__(self, connection_string: Optional[str] = None):
        if connection_string is None:
            self.connection_string = os.environ.get('MAVLINK_URL', 'udp:host.docker.internal:14550')
        else:
            self.connection_string = connection_string
            
        self._master = None
        self._is_open = False

    def connect(self) -> None:
        """Establishes the MAVLink connection and requests telemetry streams.

        Simply opening the socket is not enough: ArduPilot only ever sends
        HEARTBEAT unsolicited. GLOBAL_POSITION_INT, SYS_STATUS, VFR_HUD,
        GPS_RAW_INT and RAW_IMU are only sent on a given link if that link
        has explicitly asked for them (this is per-connection, so Mission
        Planner asking on its own link does NOT cause this link to receive
        them too). Without this request, every field except HEARTBEAT-derived
        ones stays None forever, which looks like "no live data" downstream.
        """
        if mavutil is None:
            raise MAVLinkConnectionError("pymavlink is not installed.")

        try:
            self._master = mavutil.mavlink_connection(self.connection_string)

            # Wait for the first heartbeat so target_system/target_component
            # are populated - required to address the stream request.
            heartbeat = self._master.wait_heartbeat(timeout=10)
            if heartbeat is None:
                # wait_heartbeat() does NOT raise on timeout, it returns
                # None. Treating that as "connected" leaves a dead link
                # that never produces data. Fail loudly instead.
                raise MAVLinkConnectionError(
                    "the port accepted the connection but no MAVLink "
                    "heartbeat arrived within 10s (is the simulator "
                    "running, and is another program already using this "
                    "port?)"
                )

            # Ask for every stream category at 10 Hz. MAV_DATA_STREAM_ALL
            # covers POSITION, EXTRA1/2/3, RAW_SENSORS, EXTENDED_STATUS, etc.
            self._master.mav.request_data_stream_send(
                self._master.target_system,
                self._master.target_component,
                mavutil.mavlink.MAV_DATA_STREAM_ALL,
                10,  # Hz
                1,   # start streaming
            )

            self._is_open = True
        except Exception as e:
            self._is_open = False
            if self._master is not None:
                try:
                    self._master.close()
                except Exception:
                    pass
                self._master = None
            raise MAVLinkConnectionError(f"Failed to connect to {self.connection_string}: {e}")

    @property
    def is_open(self) -> bool:
        """
        Returns True if the MAVLink transport has been successfully initialized
        and has not been closed or marked failed.
        This does NOT imply a vehicle is connected or telemetry is healthy.
        """
        return self._is_open and self._master is not None

    def receive(self) -> Optional[Any]:
        """
        Polls for the next MAVLink message non-blockingly.
        Returns the raw pymavlink message object, or None if no message is available.
        Raises MAVLinkConnectionError if not connected or if reading fails catastrophically.
        """
        if not self.is_open:
            raise MAVLinkConnectionError("Cannot receive: Transport is not open.")
            
        try:
            msg = self._master.recv_match(blocking=False)
            return msg
        except Exception as e:
            self._is_open = False
            self._master = None
            raise MAVLinkConnectionError(f"Connection lost or error reading: {e}")

    def close(self) -> None:
        """Closes the MAVLink connection."""
        if self._master:
            try:
                self._master.close()
            except Exception:
                pass
        self._master = None
        self._is_open = False