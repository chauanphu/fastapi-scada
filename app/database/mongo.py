from pymongo import MongoClient, IndexModel
from pymongo.collection import Collection
from schema.user import UserSchema
from schema.device import DeviceSchema
from utils.config import MONGO_URI
from utils.logging import logger

logger.info(f"Connecting to MongoDB: {MONGO_URI}")
client = MongoClient(
    MONGO_URI,
    connectTimeoutMS=10000, # 10 seconds
    serverSelectionTimeoutMS=10000 # 10 seconds
)
logger.info("Connected to MongoDB")
db = client["scada_db"]

def create_collection(collection_name: str, schema: dict, indexes: list = []) -> Collection:
    if collection_name not in db.list_collection_names():
        try:
            db.create_collection(collection_name)
            if schema:
                db.command({
                    "collMod": collection_name,
                    "validator": UserSchema,
                    "validationLevel": "strict",
                    "validationAction": "error"
                })
            if indexes:
                db[collection_name].create_indexes(indexes)
            logger.info(f"Created {collection_name} collection")
        except Exception as e:
            logger.error(f"Error creating {collection_name} collection: {e}")
    return db[collection_name]

def create_time_collection(collection_name: str, indexes: list = []) -> Collection:
    if collection_name not in db.list_collection_names():
        try:
            db.create_collection(
                collection_name,
                timeseries={
                    "timeField": "timestamp", 
                    "metaField": "metadata",
                    "granularity": "seconds"
                },
                expireAfterSeconds=3600 * 24 * 30 * 6 # 6 months
            )
            if indexes:
                db[collection_name].create_indexes(indexes)
            logger.info(f"Created {collection_name} collection")
        except Exception as e:
            logger.error(f"Error creating {collection_name} collection: {e}")
    return db[collection_name]

try:
    user_collection = db["users"]
    user_collection.create_index([("username", 1), ("email", 1)], unique=True)
    db.command({
        "collMod": "users",
        "validator": UserSchema,
        "validationLevel": "strict",
        "validationAction": "error"
    })
except Exception as e:
    logger.error(f"Error creating users collection: {e}")

try:
    device_collection = db["devices"]
    device_collection.create_index([("mac", 1), ("name", 1)], unique=True)
    db.command({
        "collMod": "devices",
        "validator": DeviceSchema,
        "validationLevel": "strict",
        "validationAction": "error"
    })
except Exception as e:
    logger.error(f"Error creating devices collection: {e}")

audit_collection = create_time_collection("audit", [("metadata.username",1), ("timestamp",1)]) 

sensor_collection = create_time_collection("sensors", [("metadata.mac",1), ("timestamp",1)])