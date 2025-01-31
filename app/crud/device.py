import json

import bson
from fastapi import HTTPException
from database.mongo import device_collection
from database.redis import get_redis_connection
from models.auth import Role, User
from models.device import DeviceCreate, DeviceConfigure, Device, DeviceEdit
import bson

def create_device(device: DeviceCreate) -> Device:
    new_device = device_collection.insert_one(device.model_dump())
    device = Device(
        _id=new_device.inserted_id,
        **device.model_dump()
    )
    return device

def read_device(device_id: str) -> Device | None:
    redis = get_redis_connection()
    if redis:
        mac: bytes = redis.get("id_mac:" + device_id)
        if mac:
            return read_device_by_mac(mac.decode())

    device = device_collection.find_one({"_id": bson.ObjectId(device_id)})
    if device:
        redis.set("id_mac:" + device_id, device["mac"], ex=3600)
        return Device(**device)
    return None

def read_device_by_mac(mac: str) -> Device | None:
    redis = get_redis_connection()
    if redis:
        device = redis.get(f"device:{mac}")
        if device:
            device = json.loads(device)
            return Device(**device)
    device = device_collection.find_one({"mac": mac})
    if device:
        return device
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
    return Device(**updated)

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