from pymongo import MongoClient
from pymongo.collection import Collection
from schema.user import UserSchema
from schema.device import DeviceSchema, SensorSchema
from schema.audit import AuditSchema
from utils.config import MONGO_URI
from utils.logging import logger
from pymongo.operations import IndexModel
import gridfs

logger.info(f"Connecting to MongoDB: {MONGO_URI}")
client = MongoClient(
    MONGO_URI,
    connectTimeoutMS=10000, # 10 seconds
    serverSelectionTimeoutMS=10000 # 10 seconds
)
logger.info("Connected to MongoDB")
db = client["scada_db"]
fs = gridfs.GridFS(db)

def create_collection(collection_name: str, schema: dict = None, indexes: IndexModel = None) -> Collection:
    if collection_name not in db.list_collection_names():
        try:
            device_collection = db[collection_name]
            if indexes:
                device_collection.create_index(indexes)
            if schema:
                db.command({
                    "collMod": collection_name,
                    "validator": schema,
                    "validationLevel": "strict",
                    "validationAction": "error"
                })
            logger.info(f"Created devices collection")
        except Exception as e:
            logger.error(f"Error creating devices collection: {e}")
    return db[collection_name]

def create_time_collection(collection_name: str, schema: str = None, indexes: list = []) -> Collection:
    if collection_name not in db.list_collection_names():
        try:
            db.create_collection(
                collection_name,
                timeseries={
                    "timeField": "timestamp", # Required
                    "metaField": "metadata", # Metafield for storing metadata
                    "granularity": "seconds"
                },
                expireAfterSeconds=3600 * 24 * 30 * 6 # 6 months
            )
            if indexes:
                db[collection_name].create_indexes(indexes)
            if schema:
                db.command({
                    "collMod": collection_name,
                    "validator": schema,
                    "validationLevel": "strict",
                    "validationAction": "error"
                })
            logger.info(f"Created {collection_name} collection")
        except Exception as e:
            logger.error(f"Error creating {collection_name} collection: {e}")
    return db[collection_name]

try:
    user_collection: Collection = db["users"]
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

firmware_collection: Collection = create_collection("firmware")

audit_collection = create_time_collection("audit", schema=AuditSchema, indexes=[
    IndexModel([("metadata.username", 1), ("timestamp", 1)], name="username_timestamp_idx")
])

sensor_collection = create_time_collection("sensors", schema=SensorSchema, indexes=[
    IndexModel([("metadata.mac", 1), ("timestamp", 1)], name="mac_timestamp_idx")
])

alert_collection = create_time_collection("alerts", indexes=[
    IndexModel([("metadata.device_id", 1), ("timestamp", 1)], name="mac_timestamp_idx")
])