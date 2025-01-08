from pymongo import MongoClient
from decouple import config
from pymongo.collection import Collection
from utils.logging import logger

MONGO_URI = config("MONGO_URI")
logger.info(f"Connecting to MongoDB: {MONGO_URI}")
client = MongoClient(
    MONGO_URI,
    connectTimeoutMS=10000, # 10 seconds
    serverSelectionTimeoutMS=10000 # 10 seconds
)
logger.info("Connected to MongoDB")
db = client["scada_db"]

users_collection: Collection = db["users"]