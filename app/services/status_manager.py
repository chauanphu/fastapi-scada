"""
Device Status Manager Service
Responsible for determining device status based on sensor data and working schedule
"""
import pytz
from datetime import datetime, timedelta
from models.report import SensorFull
from models.alert import DeviceState, AlertSeverity
from utils.logging import logger

local_tz = pytz.timezone('Asia/Ho_Chi_Minh')

def determine_device_status(sensor_data: SensorFull) -> tuple[DeviceState, AlertSeverity]:
    """
    Determine device status based on sensor data and working schedule
    Returns a tuple with device state and alert severity
    """
    if not sensor_data:
        return DeviceState.DISCONNECTED, AlertSeverity.CRITICAL
    try:
        # Constants
        POWER_MIN_THRESHOLD = 40
        
        # Current time
        current_time = datetime.now(pytz.UTC).astimezone(local_tz)
        
        # Extract device parameters
        working = sensor_data.power >= POWER_MIN_THRESHOLD
        toggle = sensor_data.toggle
        auto = sensor_data.auto
        voltage = sensor_data.voltage
        
        # Check if device is in working hours
        in_working_hours = _is_in_working_hours(
            current_time, 
            sensor_data.hour_on, 
            sensor_data.minute_on,
            sensor_data.hour_off, 
            sensor_data.minute_off
        )

        
        # Determine device state
        # Normal operating conditions
        if voltage > 0:
            if working and toggle:
                # Device is on and should be on
                if not auto or (auto and in_working_hours):
                    return DeviceState.WORKING, AlertSeverity.NORMAL
                # Device is on but should be off (out of working hours in auto mode)
                else:
                    return DeviceState.ON_OUT_OF_HOUR, AlertSeverity.WARNING
            
            elif not working and not toggle:
                # Device is off and should be off
                if not auto or (auto and not in_working_hours):
                    return DeviceState.OFF, AlertSeverity.NORMAL
                # Device is off but should be on (in working hours in auto mode)
                else:
                    return DeviceState.OFF_OUT_OF_HOUR, AlertSeverity.WARNING
            
            # Inconsistent states
            elif working and not toggle:
                # Device is physically on but should be off
                return DeviceState.WORKING, AlertSeverity.CRITICAL
                
            # elif not working and toggle:
            #     print(f"Power lost, due to working: {working}, toggle: {toggle}, power: {sensor_data.power}")
            #     # Device is physically off but should be on
            #     return DeviceState.POWER_LOST, AlertSeverity.CRITICAL
        
        # Critical condition: no voltage
        else:
            return DeviceState.POWER_LOST, AlertSeverity.CRITICAL
        # Default case if no condition matched
        return DeviceState.WORKING, AlertSeverity.NORMAL
        
    except Exception as e:
        logger.error(f"Error determining device status: {e}")
        return DeviceState.DISCONNECTED, AlertSeverity.CRITICAL

def _is_in_working_hours(current_time: datetime, hour_on: int, minute_on: int, 
                         hour_off: int, minute_off: int) -> bool:
    """Check if current time is within working hours"""
    # Create datetime objects for on/off times
    time_on = datetime(
        current_time.year, current_time.month, current_time.day, 
        hour_on, minute_on, tzinfo=local_tz
    )
    
    time_off = datetime(
        current_time.year, current_time.month, current_time.day, 
        hour_off, minute_off, tzinfo=local_tz
    )
    
    # Handle overnight schedules (e.g., 18:00 to 05:00)
    if hour_off < hour_on or (hour_off == hour_on and minute_off < minute_on):
        if current_time.hour < hour_off or (current_time.hour == hour_off and current_time.minute < minute_off):
            # We're in the morning before the off time
            time_on = time_on - timedelta(days=1)
        else:
            # We're in the evening after the on time
            time_off = time_off + timedelta(days=1)
    
    return time_on <= current_time <= time_off
