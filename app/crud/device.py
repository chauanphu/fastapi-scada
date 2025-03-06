import bson
from fastapi import HTTPException
from database.mongo import device_collection
from models.auth import Role, User
from models.device import DeviceCreate, DeviceConfigure, Device, DeviceEdit
from services.cache_service import cache_service

def create_device(device: DeviceCreate) -> Device:
    new_device = device_collection.insert_one(device.model_dump())
    device = Device(
        _id=new_device.inserted_id,
        **device.model_dump()
    )
    # Cache the new device
    cache_service.set_device(device)
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
        cache_service.set_device(device_obj)
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
        cache_service.set_device(device_obj)
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
    cache_service.set_device(updated)
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
        cache_service.set_device(device_obj)
    return updated

def delete_device(device_id: str) -> Device:
    device_id = bson.ObjectId(device_id)
    deleted = device_collection.find_one_and_delete({"_id": device_id})
    if deleted:
        device_obj = Device(**deleted)
        cache_service.delete_device(device_obj)
    return deleted