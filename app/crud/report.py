from database.mongo import device_collection, get_sensors_collection
from models.auth import User
from models.device import Device
from models.report import SensorModel, SensorFull
from datetime import datetime, timedelta
from database.redis import get_redis_connection
from services.alert import process_data
import json
import pytz
from crud.device import verify_owner

local_tz = pytz.timezone('Asia/Ho_Chi_Minh')  # Or your local timezone

def cache_unknown_device(mac: str) -> None:
    redis = get_redis_connection()
    # Store as member of the set unknown_devices with expiration of 1 day
    redis.sadd("unknown_devices", mac)
    redis.expire("unknown_devices", 86400)

def create_sensor_data(data: dict) -> str:
    # Check if the device exists in the database
    data["latitude"] = data["gps_lat"]
    data["longitude"] = data["gps_log"]
    del data["gps_lat"]
    del data["gps_log"]
    cached_data = mac2device(data["mac"])
    if cached_data is None:
        # Cache the unknown device
        cache_unknown_device(data["mac"])
        return None
    # Add the sensor data to device_data: power, voltage,...
    tenant_id = cached_data["tenant_id"]
    cached_data.update(data)
    sensor_data = SensorModel(**cached_data)
    device_data: SensorFull = SensorFull(**cached_data) # Enforce the model schema
    # Insert the sensor data to the database
    sensor_collection = get_sensors_collection(tenant_id)
    sensor = sensor_collection.insert_one(sensor_data.model_dump())

    # Process the data for alerting
    process_data(device_data, tenant_id)

    # Update the device data in the cache
    redis = get_redis_connection()
    if redis:
        # Check if the device exists in the cache
        redis.set(f"device:{data['mac']}", device_data.model_dump_json())

    return sensor.inserted_id

def mac2device(mac: str) -> dict:
    # Check if the device exists in the cache: device:mac -> id
    redis = get_redis_connection()
    if redis:
        device = redis.get(f"device:{mac}")
        if device:
            device = json.loads(device)
            return device
    # Check if the device exists in the database
    device = device_collection.find_one({"mac": mac})
    if device:
        # Convert ObjectId to string
        device["device_id"] = str(device["_id"])
        device["device_name"] = device["name"]
        del device["_id"]
        del device["name"]
        return device
    return None

def get_cache_status() -> list[SensorFull]:
    redis = get_redis_connection()
    if redis:
        keys: list[str] = redis.keys("device:*")
        if not keys:
            return []
        devices = redis.mget(keys)
        return [SensorFull(**json.loads(device)) for device in devices]
    return None

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
