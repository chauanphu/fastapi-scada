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
import redis
import asyncio
from redis.exceptions import RedisError
from utils.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD
from services.event_bus import event_bus
from utils.serializers import json_serialize

class CacheService:
    def __init__(self):
        self.redis = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD
        )
        self.DEVICE_KEY_PREFIX = "device:"
        self.DEVICE_TTL = 60 * 60 * 24 * 7  # 7 days
        self.IDLE_TIMEOUT = 60 * 5  # 5 minutes
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        try:
            self.redis.ping()
            return True
        except RedisError:
            return False
    
    def get_device_by_mac(self, mac: str) -> Optional[Dict[str, Any]]:
        """Get device information from cache by MAC address"""
        try:
            key = f"{self.DEVICE_KEY_PREFIX}{mac}"
            data = self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Failed to get device from cache: {e}")
            return None
    
    def get_device_by_id(self, device_id: str) -> Optional[Dict[str, Any]]:
        """Get device information from cache by device ID"""
        try:
            # This implementation depends on how you're storing devices
            # We'll need to scan for a device with matching ID
            all_devices = self.get_all_devices()
            for device in all_devices:
                if device.get("_id") == device_id:
                    return device
            return None
        except Exception as e:
            logger.error(f"Failed to get device by ID from cache: {e}")
            return None
    
    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Get all devices from cache"""
        try:
            devices = []
            keys = self.redis.keys(f"{self.DEVICE_KEY_PREFIX}*")
            for key in keys:
                data = self.redis.get(key)
                if data:
                    devices.append(json.loads(data))
            return devices
        except Exception as e:
            logger.error(f"Failed to get all devices from cache: {e}")
            return []
    
    def update_device_sensor(self, data: Dict[str, Any]) -> None:
        """Update device sensor data in cache"""
        try:
            mac = data.get("mac")
            if not mac:
                logger.error("Cannot update device without MAC address")
                return
            
            device = self.get_device_by_mac(mac)
            if not device:
                logger.warning(f"Device with MAC {mac} not found in cache, cannot update")
                return
            
            # Update the device data
            device.update(data)
            key = f"{self.DEVICE_KEY_PREFIX}{mac}"
            # Use custom serializer that handles datetime objects
            self.redis.set(key, json_serialize(device), ex=self.DEVICE_TTL)
            
            # Publish device update event using synchronous method
            # tenant_id = device.get("tenant_id")
            # if tenant_id:
            #     event_bus.publish_sync(f"device_status:{tenant_id}", device)
        except Exception as e:
            logger.error(f"Failed to update device sensor data: {e}")

    def update_device_state(self, mac: str, state: str) -> None:
        """Update device state in cache"""
        try:
            device = self.get_device_by_mac(mac)
            if not device:
                logger.warning(f"Device with MAC {mac} not found in cache, cannot update state")
                return
            
            # Update the state
            device["state"] = state
            key = f"{self.DEVICE_KEY_PREFIX}{mac}"
            # Use custom serializer that handles datetime objects
            self.redis.set(key, json_serialize(device), ex=self.DEVICE_TTL)
            
            # Publish device state update event using synchronous method
            tenant_id = device.get("tenant_id")
            if tenant_id:
                event_bus.publish_sync(f"device_status:{tenant_id}", device)
        except Exception as e:
            logger.error(f"Failed to update device state: {e}")
    
    def get_devices_with_states(self) -> List[Dict[str, Any]]:
        """Get all devices with their states from cache"""
        return self.get_all_devices()
    
    def config_settings(self, device: Device) -> None:
        """
        Save or update a device in the cache.
        Previously known as set_device.
        
        Args:
            device: The device to cache
        """
        try:
            # Get device data as dictionary
            device_data = jsonable_encoder(device)
            
            # Store by MAC address
            if device.mac:
                key = f"{self.DEVICE_KEY_PREFIX}{device.mac}"
                self.redis.set(key, json_serialize(device_data), ex=self.DEVICE_TTL)
                logger.debug(f"Device {device.mac} cached successfully")
            else:
                logger.warning(f"Cannot cache device without MAC address: {device.id}")
        except Exception as e:
            logger.error(f"Failed to cache device: {e}")
    
    def delete_device(self, device: Device) -> None:
        """
        Remove a device from the cache
        
        Args:
            device: The device to remove from cache
        """
        try:
            if device.mac:
                key = f"{self.DEVICE_KEY_PREFIX}{device.mac}"
                self.redis.delete(key)
                logger.debug(f"Device {device.mac} removed from cache")
            else:
                logger.warning(f"Cannot remove device without MAC address: {device.id}")
        except Exception as e:
            logger.error(f"Failed to remove device from cache: {e}")

# Create a singleton instance
cache_service = CacheService()