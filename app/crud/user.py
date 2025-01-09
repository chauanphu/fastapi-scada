from database.mongo import user_collection
from database.redis import get_redis_connection
import json

from models.auth import User

def create_user(user: dict) -> dict:
    return user_collection.insert_one(user)

def read_user(user_id: str) -> dict:
    # Check if the user exists in the Redis cache
    redis = get_redis_connection()
    if redis:
        user = redis.get(user_id)
        if user:
            return user
    # If the user does not exist in the Redis cache, query the MongoDB
    user = user_collection.find_one({"_id": user_id})
    if user:
        # Add the user to the Redis cache
        redis.set(user_id, user, ex=3600)
    return user

def read_user_by_username(username: str) -> User | None:
    redis = get_redis_connection()
    if redis:
        user = redis.get(username)
        user = json.loads(user)
        if user:
            user = User(**user)
            return user
    user = user_collection.find_one({"username": username})
    if user:
        user = User(**user)
        user = user.model_dump_json()
        redis.set(username, user, ex=3600)
        return user
    return None

def read_users() -> list:
    redis = get_redis_connection()
    if redis:
        users = redis.get("users")
        if users:
            users = json.loads(users)
            users = [User(**user) for user in users]
            return users
    users = list(user_collection.find())
    if users:
        users = [User(**user) for user in users]
        users = json.dumps(users)
        redis.set("users", users, ex=3600)
    return users

def update_user(user_id: str, user: dict) -> dict:
    redis = get_redis_connection()
    if redis:
        redis.set(user_id, user, ex=3600)
    return user_collection.find_one_and_update(
        {"_id": user_id},
        {"$set": user},
        return_document=True
    )

def delete_user(user_id: str) -> dict:
    redis = get_redis_connection()
    if redis:
        redis.delete(user_id)
    return user_collection.find_one_and_delete({"_id": user_id})

