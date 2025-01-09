from database.mongo import sensor_collection
from models.report import SensorModel, SensorDataBase
from datetime import datetime, timedelta

def create_sensor_data(data: SensorDataBase) -> SensorModel:
    sensor = sensor_collection.insert_one(data.model_dump())
    return sensor_collection.find_one({"_id": sensor.inserted_id})

def agg_monthly(start_date: datetime = None, end_date: datetime = None):
    # Define the date range (last 6 months by default)
    if not end_date:
        end_date = datetime.utcnow()
    if not start_date:
        start_date = end_date - timedelta(days=6 * 30)  # Approximation of 6 months

    # Aggregation pipeline
    pipeline = [
        # Match documents within the desired date range
        {"$match": {"timestamp": {"$gte": start_date, "$lte": end_date}}},
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
        {"$sort": {"_id.year": 1, "_id.month": 1}}
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
                "_id": {"$dateToString": {"format": "%Y-%m-%dT%H:00:00Z", "date": "$timestamp"}},
                "total_energy": {"$sum": "$total_energy"}
            }
        },
        # Sort by hour
        {"$sort": {"_id": 1}}
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
        {"$sort": {"_id": 1}}
    ]

    # Execute the query
    results = list(sensor_collection.aggregate(pipeline))
    return results
