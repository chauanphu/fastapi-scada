from pymongo import MongoClient
from pymongo.collection import Collection
from utils.logging import logger
from schema.user import UserSchema
from utils.config import MONGO_URI

logger.info(f"Connecting to MongoDB: {MONGO_URI}")
client = MongoClient(
    MONGO_URI,
    connectTimeoutMS=10000, # 10 seconds
    serverSelectionTimeoutMS=10000 # 10 seconds
)
logger.info("Connected to MongoDB")
db = client["scada_db"]

def create_collection(collection_name: str, schema: dict) -> Collection:
    if collection_name not in db.list_collection_names():
        try:
            db.create_collection(collection_name, validator=schema)
            logger.info(f"Created {collection_name} collection")
        # If the collection already exists, it will raise an exception
        except Exception as e:
            logger.error(f"Error creating {collection_name} collection: {e}")
    return db[collection_name]

user_collection = create_collection("users", UserSchema)