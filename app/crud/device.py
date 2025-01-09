import json

import bson
from database.mongo import device_collection
from database.redis import get_redis_connection
from models.device import DeviceCreate, DeviceConfigure, Device, DeviceEdit
from utils.logging import logger

def create_device(device: DeviceCreate) -> Device:
    try:
        new_device = device_collection.insert_one(device.model_dump())
        device = Device(
            _id=new_device.inserted_id,
            name=device.name,
            mac=device.mac,
            hour_on=device.hour_on,
            hour_off=device.hour_off,
            minute_on=device.minute_on,
            minute_off=device.minute_off,
            auto=device.auto,
            toggle=device.toggle
        )
        return device
    except Exception as e:
        logger.error(f"Error creating device: {e}")
        return None

def read_device(device_id: str) -> dict:
    redis = get_redis_connection()
    if redis:
        device = redis.get(device_id)
        if device:
            return device
    device = device_collection.find_one({"_id": device_id})
    if device:
        redis.set(device_id, device, ex=3600)
    return device

def read_device_by_mac(mac: str) -> Device | None:
    redis = get_redis_connection()
    if redis:
        device = redis.get(f"device:{mac}")
        if device:
            device = json.loads(device)
            return Device(**device)
    device = device_collection.find_one({"mac": mac})
    if device:
        device = Device(**device)
        device_data = device.model_dump_json()
        redis.set(f"device:{mac}", device_data, ex=3600)
        return device
    return None

def read_devices() -> list[Device]:
    devices = list(device_collection.find())
    if not devices:
        return []
    return [Device(**device) for device in devices]

def configure_device(device_id: str, device: DeviceConfigure) -> Device:
    try:
        # Convert _id to ObjectId
        device_id = bson.ObjectId(device_id)
        device_data = device.model_dump(exclude_unset=True)
        updated = device_collection.find_one_and_update(
            {"_id": device_id},
            {"$set": device_data},
            return_document=True
        )
    except Exception as e:
        logger.error(f"Error command device: {e}")
        return False
    return updated

def update_device(device_id: str, device: DeviceEdit) -> Device:
    device_id = bson.ObjectId(device_id)
    device_data = device.model_dump(exclude_unset=True)
    updated = device_collection.find_one_and_update(
        {"_id": device_id},
        {"$set": device_data},
        return_document=True
    )
    return updated

def delete_device(device_id: str) -> Device:
    redis = get_redis_connection()
    device_id = bson.ObjectId(device_id)
    deleted = device_collection.find_one_and_delete({"_id": device_id})
    if redis:
        redis.delete(f"device:{deleted['mac']}")
    return deleted