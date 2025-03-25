"""
## Cache Service
This service manages caching for IoT devices to reduce database access.
"""
import json
from database.mongo import device_collection
from database.redis import get_redis_connection
from models.alert import DeviceState
from models.device import Device
from utils import get_real_time
from utils.logging import logger
from typing import Optional, Dict, Any, List
from fastapi.encoders import jsonable_encoder
from utils import config

class CacheService:
    def __init__(self):
        self.redis = get_redis_connection()
        self.DEVICE_KEY_PREFIX = "device:"
        self.ID_MAC_KEY_PREFIX = "id_mac:"
        self.DEVICE_TTL = 60  # 1 hour cache expiry
        self.IDLE_TIMEOUT = config.IDLE_TIME  # 1 minute threshold for disconnected status (changed from 20)
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        try:
            return self.redis.ping()
        except Exception as e:
            logger.error(f"Redis connection error: {e}")
            return False
    
    def get_device_by_mac(self, mac: str) -> Optional[Dict[str, Any]]:
        """Get device information from cache by MAC address"""
        if not self.is_available():
            return None
        
        try:
            device_data = self.redis.get(f"{self.DEVICE_KEY_PREFIX}{mac}")
            if device_data:
                return json.loads(device_data)
            return None
        except Exception as e:
            logger.error(f"Error getting device from cache: {e}")
            return None
    
    def get_device_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device information from cache by device ID"""
        if not self.is_available():
            return None
        
        try:
            mac = self.redis.get(f"{self.ID_MAC_KEY_PREFIX}{device_id}")
            if mac:
                mac = mac.decode()
                return self.get_device_by_mac(mac)
            return None
        except Exception as e:
            logger.error(f"Error getting device from cache by ID: {e}")
            return None
    
    def get_device_state(self, device_id: str) -> Optional[str]:
        """Get the current state of a device"""
        device_data = self.get_device_by_id(device_id)
        if device_data and "state" in device_data:
            return device_data["state"]
    
    def update_device_state(self, mac: str, state: str) -> bool:
        """Update the state of a device in the cache"""
        if not self.is_available():
            return False
        
        try:
            # Get the current cached device data
            device_data = self.get_device_by_mac(mac)
            if not device_data:
                # logger.warning(f"Cannot update state for device not in cache: {mac}")
                return False
            
            # Check if we're changing from DISCONNECTED to another state
            previous_state = device_data.get("state", DeviceState.DISCONNECTED.value)

            if previous_state == DeviceState.DISCONNECTED.value and state != DeviceState.DISCONNECTED.value:
                # Update the last_seen timestamp to prevent immediate disconnection
                device_data["last_seen"] = get_real_time().timestamp()
                logger.info(f"Device {mac} reconnected, state changed from {previous_state} to {state}")
            
            # Update the state in the device data
            device_data["state"] = state
            
            # Store updated device data
            self.redis.set(
                f"{self.DEVICE_KEY_PREFIX}{mac}", 
                json.dumps(device_data),
            )
            
            return True
        except Exception as e:
            logger.error(f"Error updating device state: {e}")
            return False
    
    def set_device(self, device: Device, state: str = "") -> bool:
        """Cache device information with optional state"""
        if not self.is_available():
            return False
        
        try:
            device_data = jsonable_encoder(device)
            device_id = str(device_data.get("_id", ""))
            mac = device_data.get("mac", "")
            
            if not mac or not device_id:
                logger.warning("Invalid device data for caching: missing mac or id")
                return False
            
            # Cache only the general info and control settings; state is optional
            device_data["state"] = state or ""
            device_data["last_seen"] = get_real_time().timestamp()
            
            self.redis.set(f"{self.DEVICE_KEY_PREFIX}{mac}", json.dumps(device_data))
            self.redis.set(f"{self.ID_MAC_KEY_PREFIX}{device_id}", mac)
            return True
        except Exception as e:
            logger.error(f"Error setting device in cache: {e}")
            return False

    def delete_device(self, device: Device) -> bool:
        """Remove device from cache"""
        if not self.is_available():
            return False
        
        try:
            device_id = str(device.id)
            mac = device.mac
            
            self.redis.delete(f"{self.DEVICE_KEY_PREFIX}{mac}")
            self.redis.delete(f"{self.ID_MAC_KEY_PREFIX}{device_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting device from cache: {e}")
            return False
    
    def init_device_cache(self) -> int:
        """
        Initialize cache with all devices from database.
        Returns the number of devices cached.
        """
        if not self.is_available():
            logger.error("Cannot initialize cache: Redis not available")
            return 0
        
        try:
            # Clear existing cache keys related to devices
            keys = self.redis.keys(f"{self.DEVICE_KEY_PREFIX}*")
            keys.extend(self.redis.keys(f"{self.ID_MAC_KEY_PREFIX}*"))
            if keys:
                self.redis.delete(*keys)
                
            # Fetch all devices from database
            devices = list(device_collection.find())
            count = 0
            
            for device_data in devices:
                device = Device(**device_data)
                # Remove redundant state retrieval since only general info and control settings are cached initially
                self.set_device(device)
                count += 1
                
            logger.info(f"Cache initialized with {count} devices")
            return count
        except Exception as e:
            logger.error(f"Error initializing device cache: {e}")
            return 0
    
    def get_devices_with_states(self) -> List[Dict[str, Any]]:
        """Get all devices with their states from cache"""
        if not self.is_available():
            logger.error("Cache not available, cannot get devices with states")
            return []
        
        try:
            # Get all device keys
            device_keys = self.redis.keys(f"{self.DEVICE_KEY_PREFIX}*")
            if not device_keys:
                logger.warning("No devices found in cache")
                return []
            
            # Get all device data
            device_data_list = self.redis.mget(device_keys)
            
            # Parse JSON and ensure each device has a state
            devices = []
            for data in device_data_list:
                if data:
                    try:
                        device = json.loads(data)
                        # Use setdefault to ensure a state field exists
                        device.setdefault("state", "")
                        devices.append(device)
                    except Exception as e:
                        logger.error(f"Error parsing device data: {e}")
                        continue
            
            return devices
        except Exception as e:
            logger.error(f"Error getting devices with states: {e}")
            return []

    def update_device_sensor(self, sensor_data: dict) -> bool:
        """
        Update device cache with latest sensor data from MQTT
        This preserves existing fields like tenant_id, name, etc. while updating sensor readings
        """
        if not self.is_available():
            return False
            
        try:
            mac = sensor_data.get("mac")
            if not mac:
                logger.warning("Cannot update device: missing MAC address")
                return False
                
            # Get existing device data
            device_data = self.get_device_by_mac(mac)
            if not device_data:
                logger.warning(f"Device with MAC {mac} not found in cache")
                return False
                
            # Convert sensor_data to ensure JSON serializability (e.g., datetime objects to serializable types)
            sensor_data = jsonable_encoder(sensor_data)
                
            # Add last_seen timestamp
            device_data["last_seen"] = get_real_time().timestamp()
                
            # Merge the sensor data with existing device data
            device_data.update(sensor_data)
            
            # Simplify state preservation: if current state is DISCONNECTED, reset; otherwise preserve or default to empty
            device_data["state"] = "" if device_data.get("state") == DeviceState.DISCONNECTED.value else device_data.get("state", "")
                
            self.redis.set(
                f"{self.DEVICE_KEY_PREFIX}{mac}",
                json.dumps(device_data),
            )
            
            return True
        except Exception as e:
            logger.error(f"Error updating device with sensor data: {e}")
            return False
    
# Create a singleton instance
cache_service = CacheService()