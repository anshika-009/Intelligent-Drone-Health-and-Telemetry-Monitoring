from typing import Dict, Any, Optional
from src.parser.mavlink_parser import ParsedMAVLinkMessage

class MAVLinkNormalizer:
    """
    Converts MAVLink protocol semantics (units, raw values) into
    IDHTM canonical field names and units.
    Does NOT aggregate multiple messages into a single VehicleState.
    """
    
    def normalize(self, parsed_msg: ParsedMAVLinkMessage) -> Optional[Dict[str, Any]]:
        """
        Takes a ParsedMAVLinkMessage and returns a dictionary of normalized
        canonical fields, or None if the message is unsupported or empty.
        """
        if not parsed_msg or not hasattr(parsed_msg, 'message_type') or not hasattr(parsed_msg, 'fields'):
            return None
            
        msg_type = parsed_msg.message_type
        fields = parsed_msg.fields
        
        normalized: Dict[str, Any] = {}
        
        if msg_type == 'GLOBAL_POSITION_INT':
            if fields.get('lat') is not None:
                normalized['latitude'] = fields['lat'] / 1e7
            if fields.get('lon') is not None:
                normalized['longitude'] = fields['lon'] / 1e7
            if fields.get('relative_alt') is not None:
                normalized['altitude'] = fields['relative_alt'] / 1000.0
            if fields.get('time_boot_ms') is not None:
                normalized['source_timestamp_ms'] = fields['time_boot_ms']
                
        elif msg_type == 'SYS_STATUS':
            v_batt = fields.get('voltage_battery')
            if v_batt is not None:
                normalized['battery_voltage'] = v_batt / 1000.0
                
            b_rem = fields.get('battery_remaining')
            if b_rem is not None:
                normalized['battery_percentage'] = None if b_rem == -1 else float(b_rem)
                
            c_batt = fields.get('current_battery')
            if c_batt is not None:
                normalized['battery_current'] = None if c_batt == -1 else c_batt / 100.0
                
        elif msg_type == 'VFR_HUD':
            if fields.get('heading') is not None:
                normalized['heading'] = float(fields['heading'])
            if fields.get('airspeed') is not None:
                normalized['airspeed'] = float(fields['airspeed'])
            if fields.get('groundspeed') is not None:
                normalized['ground_speed'] = float(fields['groundspeed'])
            if fields.get('climb') is not None:
                normalized['vertical_speed'] = float(fields['climb'])
                
        elif msg_type == 'RAW_IMU':
            if fields.get('xacc') is not None:
                normalized['ax'] = fields['xacc'] * 0.00981
            if fields.get('yacc') is not None:
                normalized['ay'] = fields['yacc'] * 0.00981
            if fields.get('zacc') is not None:
                normalized['az'] = fields['zacc'] * 0.00981
                
            temp = fields.get('temperature')
            if temp is not None:
                normalized['temperature'] = None if temp == 0 else temp / 100.0
                
        elif msg_type == 'GPS_RAW_INT':
            fix = fields.get('fix_type')
            if fix is not None:
                normalized['gps_fix'] = True if fix >= 3 else False
                
            sats = fields.get('satellites_visible')
            if sats is not None:
                normalized['gps_satellites'] = None if sats == 255 else int(sats)
                
        elif msg_type == 'RADIO_STATUS':
            rssi = fields.get('rssi')
            if rssi is not None:
                if rssi == 255:
                    normalized['signal_strength'] = None
                else:
                    ss = (rssi / 254.0) * 100.0
                    normalized['signal_strength'] = max(0.0, min(100.0, ss))
                    
        elif msg_type == 'HEARTBEAT':
            if fields.get('type') is not None:
                normalized['vehicle_type'] = fields['type']
            if fields.get('autopilot') is not None:
                normalized['autopilot'] = fields['autopilot']
            if fields.get('base_mode') is not None:
                normalized['base_mode'] = fields['base_mode']
            if fields.get('custom_mode') is not None:
                normalized['custom_mode'] = fields['custom_mode']
            if fields.get('system_status') is not None:
                normalized['system_status'] = fields['system_status']
            
        else:
            return None
            
        return normalized
