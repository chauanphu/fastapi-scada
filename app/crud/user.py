import json

import bson
from database.mongo import user_collection
from database.redis import get_redis_connection
from models.user import AccountEdit, User as Account, AccountCreate
from models.auth import User
import utils.auth as auth
from utils.logging import logger

def create_user(user: AccountCreate) -> Account:
    try:
        new_user = user_collection.insert_one({
            "username": user.username,
            "hashed_password": auth.hash_password(user.password),
            "email": user.email,
            "role": user.role.value,
            "disabled": user.disabled
        })
        user = Account(
            _id=new_user.inserted_id,
            username=user.username,
            email=user.email,
            role=user.role,
            disabled=user.disabled
        )
        return user
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return None

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
        if user:
            user = json.loads(user)
            user = User(**user)
            return user
    user = user_collection.find_one({"username": username})
    if user:
        user = User(**user)
        user_data = user.model_dump_json()
        redis.set(username, user_data, ex=3600)
        return user
    return None

def read_users() -> list[Account]:
    users = list(user_collection.find())
    if not users:
        return []
    return [Account(**user) for user in users]

def update_user(user_id: str, user: AccountEdit):
    try:
        redis = get_redis_connection()
        user_data = user.model_dump()
        user_data['role'] = user_data['role'].value
        # Convert _id to ObjectId
        user_id = bson.ObjectId(user_id)
        updated = user_collection.find_one_and_update(
            {"_id": user_id},
            {"$set": user_data},
            return_document=True
        )
        if redis:
            redis.delete(user.username)
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return False
    return updated

def delete_user(user_id: str) -> Account:
    redis = get_redis_connection()
    user_id = bson.ObjectId(user_id)
    deleted = user_collection.find_one_and_delete({"_id": user_id})
    if redis:
        redis.delete(deleted['username'])
    return deleted

