"""
## Alert Service
This service is responsible for checking the status of the device and generating alerts based on the status.
"""
import json
from models.report import SensorFull
from models.alert import AlertModel, AlertModelFull, DeviceState, AlertSeverity
from datetime import datetime
import pytz
from database.mongo import get_alerts_collection
from database.redis import get_redis_connection
from utils import get_real_time
from utils.logging import logger
from services.cache_service import cache_service
from services.status_manager import determine_device_status

local_tz = pytz.timezone('Asia/Ho_Chi_Minh')  # Or your local timezone

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
    """Process sensor data to determine status and create alerts if needed"""
    try:
        # Determine device status using the status manager
        state, severity = determine_device_status(data)
        # Update the device state in the cache
        device_id = data.device_id
        mac = data.mac
        
        # Update the device state in the cache
        cache_service.update_device_state(device_id, mac, state.value)
        
        # No need to create an alert for normal status
        if severity == AlertSeverity.NORMAL:
            return
            
        # Check if this is a new state that needs an alert
        current_state = get_cached_alert(device_id)
        if current_state != state.value or not current_state:
            # Create new alert
            new_alert = AlertModel(
                state=state,
                device=device_id,
                device_name=data.device_name,
                timestamp=get_real_time(),
                severity=severity
            )
            
            # Save alert to database
            alert_collection = get_alerts_collection(tenant_id)
            alert_collection.insert_one(new_alert.model_dump())

            # Publish alert for real-time notifications
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
                
                # Check if device has a last_seen timestamp and if it's too old
                last_seen = device_data.get("last_seen")
                if not last_seen or (current_time - float(last_seen)) > cache_service.IDLE_TIMEOUT:
                    # Mark as disconnected
                    device_data["state"] = DeviceState.DISCONNECTED.value
                    
                    # Update device in cache
                    cache_service.redis.set(key, json.dumps(device_data), ex=cache_service.DEVICE_TTL)
                    
                    # Create new alert for disconnected device
                    device_id = device_data.get("_id", "")
                    device_name = device_data.get("name", "Unknown device")
                    tenant_id = device_data.get("tenant_id", "")
                    
                    if device_id and tenant_id:
                        new_alert = AlertModel(
                            state=DeviceState.DISCONNECTED,
                            device=device_id,
                            device_name=device_name,
                            timestamp=get_real_time(),
                            severity=AlertSeverity.CRITICAL
                        )
                        
                        # Save to database
                        alert_collection = get_alerts_collection(tenant_id)
                        alert_collection.insert_one(new_alert.model_dump())
                        
                        # Also update legacy state key
                        cache_service.redis.set(f"{cache_service.STATE_KEY_PREFIX}{device_id}", DeviceState.DISCONNECTED.value)
                        
                        logger.info(f"Device {device_name} marked as disconnected due to inactivity")
                        disconnected_count += 1
                    
            except Exception as e:
                logger.error(f"Error processing device {key}: {e}")
                continue
                
        return disconnected_count
    except Exception as e:
        logger.error(f"Error checking for idle devices: {e}")
        return 0
