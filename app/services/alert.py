"""
## Alert Service
This service is responsible for checking the status of the device and generating alerts based on the status.
"""
import json
from models.report import SensorFull
from models.alert import AlertModel, AlertModelFull, DeviceState, AlertSeverity
from datetime import datetime, timedelta
import pytz
from database.mongo import get_alerts_collection
from database.redis import get_redis_connection
from utils import get_real_time
from utils.logging import logger
from services.cache_service import cache_service

local_tz = pytz.timezone('Asia/Ho_Chi_Minh')  # Or your local timezone

class Alert:
    def __init__(self, sensor_data: SensorFull = None):
        self.sensor_data = sensor_data
        self.POWER_MINTHRESHOLD = 40
        self.current_time = datetime.now(pytz.UTC).astimezone(local_tz)

    def check_power(self):
        return self.sensor_data.power >= self.POWER_MINTHRESHOLD
    
    def in_working_hours(self):
        # Assume hour_on (18) > hour_off (5). Working in night time

        time_off = datetime(
            self.current_time.year, self.current_time.month, self.current_time.day, self.sensor_data.hour_off, self.sensor_data.minute_off,
            tzinfo=local_tz)
        # Time off is in the next day
        if self.sensor_data.hour_off < self.sensor_data.hour_on:
            time_off += timedelta(days=1)
        time_on = datetime(self.current_time.year, self.current_time.month, self.current_time.day, self.sensor_data.hour_on, self.sensor_data.minute_on,
                           tzinfo=local_tz)
        
        return time_on <= self.current_time <= time_off

    def check_status(self) -> tuple[DeviceState, AlertSeverity]:
        if self.sensor_data:
            working = self.check_power()
            on_working_hours = self.in_working_hours()
            toggle = self.sensor_data.toggle
            auto = self.sensor_data.auto
            voltage = self.sensor_data.voltage

            # Normal conditions
            ## Device is on manually or automatically during working hours
            if voltage > 0 and (working and toggle) and (not auto or (auto and on_working_hours)):
                return DeviceState.WORKING, AlertSeverity.NORMAL
            elif not working and not toggle and not on_working_hours and auto:
                return DeviceState.OFF, AlertSeverity.NORMAL
            ## Device is off manually or automatically when out of working hours
            elif voltage > 0 and (working and not toggle) and (not auto or (auto and not on_working_hours)):
                return DeviceState.OFF, AlertSeverity.NORMAL
            # Critical conditions
            ## Devie is lost power
            elif voltage == 0 or (not working and toggle):
                return DeviceState.POWER_LOST, AlertSeverity.CRITICAL
            elif not working and toggle:
                return DeviceState.POWER_LOST, AlertSeverity.CRITICAL
            ## Device is still on despite switching down
            elif working and not toggle:
                return DeviceState.WORKING, AlertSeverity.CRITICAL
            # Warning conditions
            ## Device is on out of working hours
            elif working and auto and not on_working_hours:
                return DeviceState.ON_OUT_OF_HOUR, AlertSeverity.WARNING
            ## Device is off out of working hours
            elif not working and auto and on_working_hours:
                return DeviceState.OFF_OUT_OF_HOUR, AlertSeverity.WARNING
            else:
                return DeviceState.WORKING, AlertSeverity.NORMAL
        else: 
            return DeviceState.DISCONNECTED, AlertSeverity.CRITICAL
        
def get_cached_alert(device_id: str) -> str:
    """Get the device state from cache"""
    device_data = cache_service.get_device_by_id(device_id)
    if device_data and "state" in device_data:
        return device_data["state"]
    
    # Fallback to legacy method
    redis = get_redis_connection()
    if redis:
        cached_alert = redis.get("state:" + device_id)
        return cached_alert.decode("utf-8") if cached_alert else ""
    return ""

# Pub/sub latest alert message
def subscribe_alert():
    redis = get_redis_connection()
    pubsub = redis.pubsub()
    return pubsub

def publish_alert(message: AlertModel, tenant_id: str):
    redis = get_redis_connection()
    redis.publish("alert:" + tenant_id, message.model_dump_json())

def reset_alert_count(device_id: str):
    redis = get_redis_connection()
    redis.set("alert_count:" + device_id, 0)

def process_data(data: SensorFull, tenant_id: str):
    try:
        alert = Alert(data)
        state, severity = alert.check_status()
        
        # Update the device state in the cache
        device_id = data.device_id
        mac = data.mac
        
        # Update the device state in the cache
        # Note: update_device_with_sensor_data already adds a timestamp
        cache_service.update_device_state(device_id, mac, state.value)
        
        if severity == AlertSeverity.NORMAL:
            return
            
        current_state = get_cached_alert(device_id)
        # If the current state is not the same as the new state, update the alert
        if current_state != state.name or not current_state:
            new_alert = AlertModel(
                state=state,
                device=device_id,
                device_name=data.device_name,
                timestamp=alert.current_time,
                severity=severity
            )
            alert_collection = get_alerts_collection(tenant_id)
            alert_collection.insert_one(new_alert.model_dump())

            # Convert to AlertModelFull
            full_alert = AlertModelFull(**new_alert.model_dump(), mac=data.mac, tenant_id=tenant_id)
            publish_alert(full_alert, tenant_id)

    except Exception as e:
        logger.error(f"Failed to process alert data: {e}")
        return

def check_idle_devices() -> int:
    """
    Check all devices and mark as disconnected if they've been idle for too long
    Returns the number of devices marked as disconnected
    """
    if not cache_service.is_available():
        return 0
        
    try:
        # Get all device keys
        device_keys = cache_service.redis.keys(f"{cache_service.DEVICE_KEY_PREFIX}*")
        if not device_keys:
            return 0
            
        # Current timestamp for comparison
        current_time = get_real_time().timestamp()
        disconnected_count = 0
        
        # Check each device
        for key in device_keys:
            try:
                device_data = json.loads(cache_service.redis.get(key))
                
                # Skip devices that are already marked as disconnected
                if device_data.get("state") == DeviceState.DISCONNECTED.value:
                    continue
                
                # If the device has been idle for too long or no last_seen timestamp
                last_seen = device_data.get("last_seen")
                if not last_seen or (current_time - last_seen) > cache_service.IDLE_TIMEOUT:
                    # Mark as disconnected
                    device_data["state"] = DeviceState.DISCONNECTED.value
                    
                    # Update device in cache
                    cache_service.redis.set(key, json.dumps(device_data), ex=cache_service.DEVICE_TTL)
                    # Add new alert to the database
                    new_alert = AlertModel(
                        state=DeviceState.DISCONNECTED,
                        device=device_data.get("_id", ""),
                        device_name=device_data.get("name", ""),
                        timestamp=current_time,
                        severity=AlertSeverity.CRITICAL
                    )
                    alert_collection = get_alerts_collection(device_data.get("tenant_id", ""))
                    alert_collection.insert_one(new_alert.model_dump())

                    # Also update legacy state key
                    device_id = str(device_data.get("_id", ""))
                    if device_id:
                        cache_service.redis.set(f"{cache_service.STATE_KEY_PREFIX}{device_id}", DeviceState.DISCONNECTED.value)
                        
                    disconnected_count += 1
                    logger.info(f"Device {device_data.get('name', key.decode().split(':')[-1])} marked as disconnected due to inactivity")
                    
            except Exception as e:
                logger.error(f"Error processing device {key}: {e}")
                continue
                
        return disconnected_count
    except Exception as e:
        logger.error(f"Error checking for idle devices: {e}")
        return 0
