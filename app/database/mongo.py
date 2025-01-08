from pymongo import MongoClient
from decouple import config
from pymongo.collection import Collection
from utils.logging import logger

logger.info("Connecting to MongoDB")
MONGO_URI = config("MONGO_URI")
logger.info(f"MongoDB URI: {MONGO_URI}")
client = MongoClient(MONGO_URI)
db = client["scada_db"]

users_collection: Collection = db["users"]