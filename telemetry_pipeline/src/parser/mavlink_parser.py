from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class ParsedMAVLinkMessage:
    """A strictly typed container for a parsed MAVLink message without normalization."""
    message_type: str
    fields: Dict[str, Any]

class MAVLinkParser:
    """
    Parses raw MAVLink message objects into a structured dictionary of fields.
    Does NOT normalize units, rename fields, or calculate freshness.
    """
    
    def parse(self, msg: Any) -> Optional[ParsedMAVLinkMessage]:
        """
        Parses a single pymavlink message.
        Returns None if the message type is unsupported or if the message is malformed.
        """
        if not hasattr(msg, 'get_type'):
            return None
            
        try:
            msg_type = msg.get_type()
        except (AttributeError, TypeError):
            return None
            
        if msg_type == 'GLOBAL_POSITION_INT':
            return ParsedMAVLinkMessage(
                message_type=msg_type,
                fields={
                    'lat': getattr(msg, 'lat', None),
                    'lon': getattr(msg, 'lon', None),
                    'relative_alt': getattr(msg, 'relative_alt', None),
                    'time_boot_ms': getattr(msg, 'time_boot_ms', None)
                }
            )
        elif msg_type == 'SYS_STATUS':
            return ParsedMAVLinkMessage(
                message_type=msg_type,
                fields={
                    'voltage_battery': getattr(msg, 'voltage_battery', None),
                    'battery_remaining': getattr(msg, 'battery_remaining', None),
                    'current_battery': getattr(msg, 'current_battery', None)
                }
            )
        elif msg_type == 'VFR_HUD':
            return ParsedMAVLinkMessage(
                message_type=msg_type,
                fields={
                    'heading': getattr(msg, 'heading', None),
                    'airspeed': getattr(msg, 'airspeed', None),
                    'groundspeed': getattr(msg, 'groundspeed', None),
                    'climb': getattr(msg, 'climb', None)
                }
            )
        elif msg_type == 'RAW_IMU':
            return ParsedMAVLinkMessage(
                message_type=msg_type,
                fields={
                    'xacc': getattr(msg, 'xacc', None),
                    'yacc': getattr(msg, 'yacc', None),
                    'zacc': getattr(msg, 'zacc', None),
                    'temperature': getattr(msg, 'temperature', None),
                    'time_usec': getattr(msg, 'time_usec', None)
                }
            )
        elif msg_type == 'GPS_RAW_INT':
            return ParsedMAVLinkMessage(
                message_type=msg_type,
                fields={
                    'fix_type': getattr(msg, 'fix_type', None),
                    'satellites_visible': getattr(msg, 'satellites_visible', None),
                    'time_usec': getattr(msg, 'time_usec', None)
                }
            )
        elif msg_type == 'RADIO_STATUS':
            return ParsedMAVLinkMessage(
                message_type=msg_type,
                fields={
                    'rssi': getattr(msg, 'rssi', None)
                }
            )
        elif msg_type == 'HEARTBEAT':
            return ParsedMAVLinkMessage(
                message_type=msg_type,
                fields={
                    'type': getattr(msg, 'type', None),
                    'autopilot': getattr(msg, 'autopilot', None),
                    'base_mode': getattr(msg, 'base_mode', None),
                    'custom_mode': getattr(msg, 'custom_mode', None),
                    'system_status': getattr(msg, 'system_status', None)
                }
            )
            
        return None

