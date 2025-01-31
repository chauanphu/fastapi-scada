from pymongo import MongoClient
from pymongo.collection import Collection
from schema.user import UserSchema
from schema.device import DeviceSchema
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

# Define global collections: users, tenants
def get_users_collection() -> Collection:
    return client["scada_db"]["users"]

def get_tenants_collection() -> Collection:
    return client["scada_db"]["tenants"]

# Resources for each tenant
def create_tenant_db(tenant_id: str) -> Collection:
    db = client["tenant_" + tenant_id]
    fs = gridfs.GridFS(db)
    create_time_collection(db, "audit", indexes=[
        IndexModel([("metadata.username", 1), ("timestamp", 1)], name="username_timestamp_idx")
    ])

    create_time_collection(db, "sensors", indexes=[
        IndexModel([("metadata.device_id", 1), ("metadata.mac", 1), ("timestamp", 1)], name="mac_timestamp_idx")
    ])

    create_time_collection(db, "alerts", indexes=[
        IndexModel([("metadata.device_id", 1), ("timestamp", 1)], name="mac_timestamp_idx")
    ])

def delete_tenant_db(tenant_id: str):
    client.drop_database("tenant_" + tenant_id)

def get_tenant_db(tenant_id: str) -> Collection:
    return client["tenant_" + tenant_id]

def create_collection(database, collection_name: str, schema: dict = None, indexes: IndexModel = None) -> Collection:
    if collection_name not in database.list_collection_names():
        try:
            device_collection = database[collection_name]
            if indexes:
                device_collection.create_index(indexes)
            if schema:
                database.command({
                    "collMod": collection_name,
                    "validator": schema,
                    "validationLevel": "strict",
                    "validationAction": "error"
                })
            logger.info(f"Created devices collection")
        except Exception as e:
            logger.error(f"Error creating devices collection: {e}")
    return database[collection_name]

def create_time_collection(database, collection_name: str, indexes: list = []) -> Collection:
    if collection_name not in database.list_collection_names():
        try:
            database.create_collection(
                collection_name,
                timeseries={
                    "timeField": "timestamp", # Required
                    "metaField": "metadata", # Metafield for storing metadata
                    "granularity": "seconds"
                },
                expireAfterSeconds=3600 * 24 * 30 * 6 # 6 months
            )
            if indexes:
                database[collection_name].create_indexes(indexes)
            logger.info(f"Created {collection_name} collection")
        except Exception as e:
            logger.error(f"Error creating {collection_name} collection: {e}")
    return database[collection_name]

def get_devices_collection(tenant_id: str) -> Collection:
    return get_tenant_db(tenant_id)["devices"]

def get_audit_collection(tenant_id: str) -> Collection:
    return get_tenant_db(tenant_id)["audit"]

def get_alerts_collection(tenant_id: str) -> Collection:
    return get_tenant_db(tenant_id)["alerts"]

def get_sensors_collection(tenant_id: str) -> Collection:
    return get_tenant_db(tenant_id)["sensors"]

def get_fs() -> gridfs.GridFS:
    collection: Collection = client["scada_db"]
    return gridfs.GridFS(collection)


global_db = client["scada_db"]

try:
    user_collection: Collection = global_db["users"]
    user_collection.create_index([("username", 1), ("email", 1)], unique=True)
    global_db.command({
        "collMod": "users",
        "validator": UserSchema,
        "validationLevel": "strict",
        "validationAction": "error"
    })

except Exception as e:
    logger.error(f"Error creating users collection: {e}")

try:
    device_collection = global_db["devices"]
    device_collection.create_index([("mac", 1), ("name", 1)], unique=True)
    global_db.command({
        "collMod": "devices",
        "validator": DeviceSchema,
        "validationLevel": "strict",
        "validationAction": "error"
    })
except Exception as e:
    logger.error(f"Error creating devices collection: {e}")

user_collection = get_users_collection()
tenant_collection = get_tenants_collection()