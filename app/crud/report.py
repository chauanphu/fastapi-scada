from database.mongo import device_collection, get_sensors_collection
from models.auth import User
from models.device import Device
from models.report import SensorModel, SensorFull
from datetime import datetime, timedelta
from database.redis import get_redis_connection
import json
import pytz
from crud.device import verify_owner
from services.cache_service import cache_service

local_tz = pytz.timezone('Asia/Ho_Chi_Minh')  # Or your local timezone

def cache_unknown_device(mac: str) -> None:
    redis = get_redis_connection()
    # Store as member of the set unknown_devices with expiration of 1 minute
    redis.sadd("unknown_devices", mac)
    redis.expire("unknown_devices", 60)

def add_data(data: SensorModel, tenant_id: str) -> str:
    """
    Insert sensor data into MongoDB, avoiding redundancy.
    Assumes data has already been preprocessed and contains tenant_id.
    """
    # Get the sensor collection for the tenant
    sensor_collection = get_sensors_collection(tenant_id)
    
    # Check if sensor data with same device_id and timestamp already exists
    existing = sensor_collection.find_one({
        "device_id": data.device_id,
        "timestamp": data.timestamp
    })
    
    if existing:
        return existing.get("_id")
        
    # Insert the sensor data
    sensor = sensor_collection.insert_one(data.model_dump())
    return sensor.inserted_id

def mac2device(mac: str) -> dict:
    # Check if the device exists in the cache
    device = cache_service.get_device_by_mac(mac)
    if device:
        # Ensure device_id and device_name are set properly
        device["device_id"] = str(device["_id"])
        device["device_name"] = device["name"]
        return device
        
    # Fallback to database
    device = device_collection.find_one({"mac": mac})
    if device:
        # Convert ObjectId to string
        device["device_id"] = str(device["_id"])
        device["device_name"] = device["name"]
        del device["_id"]
        del device["name"]
        # Cache the device for future use
        cache_service.set_device(Device(**device))
        return device
    return None

def get_cache_status() -> list[SensorFull]:
    devices = []
    redis = get_redis_connection()
    if redis:
        keys = redis.keys(f"device:*")
        if not keys:
            return []
        device_data = redis.mget(keys)
        for data in device_data:
            if data:
                try:
                    devices.append(SensorFull(**json.loads(data)))
                except Exception:
                    pass
    return devices

def agg_monthly(current_user: User, device_id: str, start_date: datetime = None, end_date: datetime = None):
    device: Device = verify_owner(current_user, device_id)
    # Define the date range (last 6 months by default)
    if not end_date:
        end_date = datetime.now(pytz.UTC).astimezone(local_tz)
    if not start_date:
        start_date = end_date - timedelta(days=6 * 30)  # Approximation of 6 months

    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999)
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Aggregation pipeline
    pipeline = [
        # Match documents within the desired date range
        {"$match": 
            {
                "timestamp": {"$gte": start_date, "$lte": end_date},
                "device_id": device_id
            },
        },
        # Group by year and month (extract year and month from the timestamp)
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$timestamp"},
                    "month": {"$month": "$timestamp"}
                },
                "total_energy": {"$sum": "$total_energy"}
            }
        },
        # Sort by year and month
        {"$sort": {"_id.year": 1, "_id.month": 1}},
        # Project the result to timestamp and total_energy
        {"$project": {"_id": 0, "timestamp": {"$dateFromParts": {"year": "$_id.year", "month": "$_id.month"}}, "total_energy": 1}}
    ]
    sensor_collection = get_sensors_collection(device.tenant_id)
    results = list(sensor_collection.aggregate(pipeline))
    return results

def agg_daily(current_user: User, device_id: str, start_date: datetime = None, end_date: datetime = None):
    device: Device = verify_owner(current_user, device_id)
    # Define the date range (last 30 days by default)
    if not end_date:
        end_date = datetime.now(pytz.UTC).astimezone(local_tz).replace(hour=23, minute=59, second=59, microsecond=999999)
    if not start_date:
        start_date = end_date - timedelta(days=30)
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

    # Aggregation pipeline
    pipeline = [
        # Match documents within the desired day
        {"$match": {"timestamp": {"$gte": start_date, "$lte": end_date}, "device_id": device_id}},
        # Group by hour (using $dateToString to extract hour)
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$timestamp"},
                    "month": {"$month": "$timestamp"},
                    "day": {"$dayOfMonth": "$timestamp"}
                },
                "total_energy": {"$sum": "$total_energy"}
            }
        },
        # Sort by hour
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "timestamp": {"$dateFromParts": {"year": "$_id.year", "month": "$_id.month", "day": "$_id.day"}}, "total_energy": 1}}
    ]
    sensor_collection = get_sensors_collection(device.tenant_id)
    # Run the query
    results = list(sensor_collection.aggregate(pipeline))
    return results

def agg_hourly(current_user: User, device_id: str, start_date: datetime = None, end_date: datetime = None):
    device: Device = verify_owner(current_user, device_id)
    # Define the date range (24 hours by default)
    if not end_date:
        end_date = datetime.now(pytz.UTC).astimezone(local_tz)
    if not start_date:
        start_date = end_date - timedelta(days=1)
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    # Aggregation pipeline
    pipeline = [
        # Match documents within the desired day
        {"$match": {"timestamp": {"$gte": start_date, "$lte": end_date}, "device_id": device_id}},
        # Group by hour (extract hour from the timestamp)
        {
            "$group": {
                "_id": {"$hour": "$timestamp"},
                "total_energy": {"$sum": "$total_energy"}
            }
        },
        # Sort by hour
        {"$sort": {"_id": 1}},
        # Project the result to timestamp and total_energy
        {"$project": {
            "_id": 0,
            "timestamp": {
                "$dateFromParts": {
                    "year": {"$year": "$$NOW"},
                    "month": {"$month": "$$NOW"},
                    "day": {"$dayOfMonth": "$$NOW"},
                    "hour": "$_id"
                }
            },
            "total_energy": 1
        }}
    ]
    sensor_collection = get_sensors_collection(device.tenant_id)

    # Execute the query
    results = list(sensor_collection.aggregate(pipeline))
    return results
