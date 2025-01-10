from database.mongo import sensor_collection, device_collection
from models.report import SensorDataResponse
from datetime import datetime, timedelta
from models.report import SensorDataResponse
from database.redis import get_redis_connection
import json
import bson
    
def create_sensor_data(data: dict):
    # Check if the device exists in the database
    device_data: dict = mac2id(data["mac"])
    if device_data is None:
        return None
    # Add the sensor data to device_data: power, voltage,...
    device_data.update(data)
    device_data: SensorDataResponse = SensorDataResponse(**device_data) # Enforce the model schema
    sensor = sensor_collection.insert_one(device_data.model_dump())
    redis = get_redis_connection()
    if redis:
        # Check if the device exists in the cache
        redis.set(f"device:{data['mac']}", device_data.model_dump_json())

    return sensor.inserted_id

def mac2id(mac: str) -> str:
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
        del device["_id"]
        redis.set(f"device:{mac}", json.dumps(device))
        return device
    return None

def get_cache_status() -> list[SensorDataResponse]:
    redis = get_redis_connection()
    if redis:
        keys: list[str] = redis.keys("device:*")
        if not keys:
            return []
        devices = redis.mget(keys)
        return [SensorDataResponse(**json.loads(device)) for device in devices]
    return None

def agg_monthly(start_date: datetime = None, end_date: datetime = None, device_id: str = None):
    # Define the date range (last 6 months by default)
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=6 * 30)  # Approximation of 6 months

    # Aggregation pipeline
    pipeline = [
        # Match documents within the desired date range
        {"$match": 
            {
                "timestamp": {"$gte": start_date, "$lte": end_date},
                "_id": device_id
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

    # Execute the query
    results = list(sensor_collection.aggregate(pipeline))
    return results

def agg_daily(start_date: datetime = None, end_date: datetime = None):
    # Define the date range (last 30 days by default)
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=30)

    # Aggregation pipeline
    pipeline = [
        # Match documents within the desired day
        {"$match": {"timestamp": {"$gte": start_date, "$lte": end_date}}},
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

    # Run the query
    results = list(sensor_collection.aggregate(pipeline))
    return results

def agg_hourly(start_of_day: datetime = None, end_of_day: datetime = None):
    # Define the date range (24 hours by default)
    if not end_of_day:
        end_of_day = datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999)
    if not start_of_day:
        start_of_day = end_of_day - timedelta(days=1)

    # Aggregation pipeline
    pipeline = [
        # Match documents within the desired day
        {"$match": {"timestamp": {"$gte": start_of_day, "$lte": end_of_day}}},
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

    # Execute the query
    results = list(sensor_collection.aggregate(pipeline))
    print(results)
    return results
