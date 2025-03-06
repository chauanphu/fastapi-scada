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
from typing import Optional, Dict, Any, List, Union
from fastapi.encoders import jsonable_encoder

class CacheService:
    def __init__(self):
        self.redis = get_redis_connection()
        self.DEVICE_KEY_PREFIX = "device:"
        self.ID_MAC_KEY_PREFIX = "id_mac:"
        self.STATE_KEY_PREFIX = "state:"  # Legacy, for backward compatibility
        self.DEVICE_TTL = 3600  # 1 hour cache expiry
        self.IDLE_TIMEOUT = 300  # 5 minutes threshold for disconnected status
    
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
            
        # Fallback to legacy key
        if not self.is_available():
            return None
        
        try:
            state = self.redis.get(f"{self.STATE_KEY_PREFIX}{device_id}")
            return state.decode("utf-8") if state else ""
        except Exception as e:
            logger.error(f"Error getting device state: {e}")
            return None
    
    def update_device_state(self, device_id: str, mac: str, state: str) -> bool:
        """Update the state of a device in the cache"""
        if not self.is_available():
            return False
        
        try:
            # Get the current cached device data
            device_data = self.get_device_by_mac(mac)
            if not device_data:
                # If device isn't in cache, we can't update its state
                logger.warning(f"Cannot update state for device not in cache: {mac}")
                # Still set the legacy state key for backward compatibility
                self.redis.set(f"{self.STATE_KEY_PREFIX}{device_id}", state)
                return False
            
            # Update the state in the device data
            device_data["state"] = state
            
            # Store updated device data
            self.redis.set(
                f"{self.DEVICE_KEY_PREFIX}{mac}", 
                json.dumps(device_data),
                ex=self.DEVICE_TTL
            )
            
            # Also update the legacy state key for backward compatibility
            self.redis.set(f"{self.STATE_KEY_PREFIX}{device_id}", state)
            
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
                logger.warning(f"Invalid device data for caching: missing mac or id")
                return False
            
            # Include state in device data
            device_data["state"] = state
            # Add last_seen timestamp
            device_data["last_seen"] = get_real_time().timestamp()
            
            # Store device data by MAC address
            self.redis.set(
                f"{self.DEVICE_KEY_PREFIX}{mac}", 
                json.dumps(device_data),
                ex=self.DEVICE_TTL
            )
            
            # Store mapping from device_id to MAC
            self.redis.set(
                f"{self.ID_MAC_KEY_PREFIX}{device_id}", 
                mac,
                ex=self.DEVICE_TTL
            )
            
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
    
    def initialize_device_cache(self) -> int:
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
                device_id = str(device.id)
                
                # Get current state if exists
                state = ""
                try:
                    state_key = f"{self.STATE_KEY_PREFIX}{device_id}"
                    state_bytes = self.redis.get(state_key)
                    if state_bytes:
                        state = state_bytes.decode("utf-8")
                except Exception:
                    pass
                
                # Cache the device with its state
                self.set_device(device, state)
                count += 1
                
            logger.info(f"Cache initialized with {count} devices")
            return count
        except Exception as e:
            logger.error(f"Error initializing device cache: {e}")
            return 0
            
    def update_device_in_cache(self, device: Device) -> bool:
        """Update device information in cache"""
        return self.set_device(device)
    
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
                        # Make sure device has a state field (even if it's empty)
                        if "state" not in device:
                            device["state"] = ""
                        devices.append(device)
                    except Exception as e:
                        logger.error(f"Error parsing device data: {e}")
                        continue
            
            return devices
        except Exception as e:
            logger.error(f"Error getting devices with states: {e}")
            return []

    def update_device_with_sensor_data(self, sensor_data: dict) -> bool:
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
                
            # Add last_seen timestamp
            device_data["last_seen"] = get_real_time().timestamp()
                
            # Merge the sensor data with existing device data
            # This preserves important fields like tenant_id, name, etc.
            device_data.update(sensor_data)
            
            # Preserve state if it exists
            if "state" not in device_data:
                device_data["state"] = ""
                
            # Store updated device data
            self.redis.set(
                f"{self.DEVICE_KEY_PREFIX}{mac}",
                json.dumps(jsonable_encoder(device_data)),
                ex=self.DEVICE_TTL
            )
            
            return True
        except Exception as e:
            logger.error(f"Error updating device with sensor data: {e}")
            return False
    
    def check_idle_devices(self) -> int:
        """
        Check all devices and mark as disconnected if they've been idle for too long
        Returns the number of devices marked as disconnected
        """
        if not self.is_available():
            return 0
            
        try:
            # Get all device keys
            device_keys = self.redis.keys(f"{self.DEVICE_KEY_PREFIX}*")
            if not device_keys:
                return 0
                
            # Current timestamp for comparison
            current_time = get_real_time().timestamp()
            disconnected_count = 0
            
            # Check each device
            for key in device_keys:
                try:
                    device_data = json.loads(self.redis.get(key))
                    
                    # Skip devices that are already marked as disconnected
                    if device_data.get("state") == DeviceState.DiSCONNECTED.value:
                        continue
                    
                    # If the device has been idle for too long or no last_seen timestamp
                    last_seen = device_data.get("last_seen")
                    if not last_seen or (current_time - last_seen) > self.IDLE_TIMEOUT:
                        # Mark as disconnected
                        device_data["state"] = DeviceState.DiSCONNECTED.value
                        
                        # Update device in cache
                        self.redis.set(key, json.dumps(device_data), ex=self.DEVICE_TTL)
                        
                        # Also update legacy state key
                        device_id = str(device_data.get("_id", ""))
                        if device_id:
                            self.redis.set(f"{self.STATE_KEY_PREFIX}{device_id}", DeviceState.DiSCONNECTED.name)
                            
                        disconnected_count += 1
                        logger.info(f"Device {device_data.get('name', key.decode().split(':')[-1])} marked as disconnected due to inactivity")
                        
                except Exception as e:
                    logger.error(f"Error processing device {key}: {e}")
                    continue
                    
            return disconnected_count
        except Exception as e:
            logger.error(f"Error checking for idle devices: {e}")
            return 0

# Create a singleton instance
cache_service = CacheService()
