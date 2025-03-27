import bson
from fastapi import HTTPException
from database.mongo import device_collection
from models.auth import Role, User
from models.device import DeviceCreate, DeviceConfigure, Device, DeviceEdit
from services.cache_service import cache_service
from utils.logging import logger

def create_device(device: DeviceCreate) -> Device:
    new_device = device_collection.insert_one(device.model_dump())
    device = Device(
        _id=new_device.inserted_id,
        **device.model_dump()
    )
    # Cache the new device
    cache_service.config_settings(device)
    return device

def read_device(device_id: str) -> Device | None:
    # Try to get from cache first
    cached_device = cache_service.get_device_by_id(device_id)
    if cached_device:
        return Device(**cached_device)
        
    # Fallback to database
    device = device_collection.find_one({"_id": bson.ObjectId(device_id)})
    if device:
        device_obj = Device(**device)
        cache_service.config_settings(device_obj)
        return device_obj
    return None

def read_device_by_mac(mac: str) -> Device | None:
    # Try to get from cache first
    cached_device = cache_service.get_device_by_mac(mac)
    if cached_device:
        return Device(**cached_device)
        
    # Fallback to database
    device = device_collection.find_one({"mac": mac})
    if device:
        device_obj = Device(**device)
        cache_service.config_settings(device_obj)
        return device_obj
    return None

def read_devices(tenant_id: str = "") -> list[Device]:
    if tenant_id:
        devices = list(device_collection.find({"tenant_id": tenant_id}))
    else:
        devices = list(device_collection.find())
    if not devices:
        return []
    return [Device(**device) for device in devices]

async def init():
        """
        Initialize cache with all devices from database.
        Caches general information, control settings and sets default state.
        
        Args:
            db: Database session
        """
        try:
            logger.info("Initializing device cache from database")
            devices = await get_all_devices()
            cache_service.clear()
            cache_service.cache_device(devices)
        except Exception as e:
            logger.error(f"Failed to initialize device cache: {e}")

async def get_all_devices() -> list[Device]:
    """
    Get all devices from database.
    This function is used primarily for cache initialization.
    
    Args:
        db: Optional database session (not used with MongoDB but kept for interface consistency)
        
    Returns:
        List of Device objects
    """
    try:
        devices = list(device_collection.find())
        if not devices:
            return []
        return [Device(**device) for device in devices]
    except Exception as e:
        # Log error but don't raise to prevent cache initialization failure
        import logging
        logging.error(f"Failed to get devices from database: {e}")
        return []

def verify_owner(current_user: User, device_id: str) -> dict:
    # Check if the device exists in the database
    device = read_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    if current_user.role == Role.SUPERADMIN or device.tenant_id == current_user.tenant_id:
        return device
    raise HTTPException(status_code=401, detail="Device does not belong to the tenant")

def configure_device(current_user: User, device_id: str, device: DeviceConfigure) -> Device:
    # Check if the device belongs to the tenant
    device: Device = verify_owner(current_user, device_id)
    # Convert _id to ObjectId
    device_id = bson.ObjectId(device_id)
    device_data = device.model_dump(exclude_unset=True)
    updated = device_collection.find_one_and_update(
        {"_id": device_id},
        {"$set": device_data},
        return_document=True
    )
    if not updated:
        raise HTTPException(status_code=400, detail="Failed to update device")
    
    updated = Device(**updated)
    # Update device in cache
    cache_service.config_settings(updated)
    return updated

def update_device(device_id: str, device: DeviceEdit) -> Device:
    device_id = bson.ObjectId(device_id)
    device_data = device.model_dump(exclude_unset=True)
    updated = device_collection.find_one_and_update(
        {"_id": device_id},
        {"$set": device_data},
        return_document=True
    )
    # Update the device in cache
    if updated:
        device_obj = Device(**updated)
        cache_service.config_settings(device_obj)
    return updated

def delete_device(device_id: str) -> Device:
    device_id = bson.ObjectId(device_id)
    deleted = device_collection.find_one_and_delete({"_id": device_id})
    if deleted:
        device_obj = Device(**deleted)
        cache_service.delete_device(device_obj)
    return deleted