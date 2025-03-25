import redis
import redis.asyncio
from datetime import timedelta
from typing import Callable, Coroutine
from redis.exceptions import ConnectionError

from utils.config import REDIS_HOST, REDIS_PORT, REDIS_DB, REDIS_PASSWORD
from utils.logging import logger

# Existing synchronous connection
def get_redis_connection():
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True
    )

# New asynchronous connection
async def get_async_redis_connection():
    return redis.asyncio.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        db=REDIS_DB,
        password=REDIS_PASSWORD,
        decode_responses=True
    )

# Add a refresh token into Redis list with expiration time
def set_refresh_token(token, expires: timedelta):
    redis = get_redis_connection()
    try:
        if redis:
            # Add the refresh token to the Redis list with an expiration time
            redis.set(f"rtoken:{token}", "", ex=expires)
            return True
        return False
    except Exception as e:
        logger.error(f"Error setting refresh token: {e}")
        return False

# Check if the refresh token exists in the Redis list
def check_refresh_token(token):
    redis = get_redis_connection()
    if redis:
        return redis.exists(f"rtoken:{token}")
    return False

# Remove the refresh token from the Redis list
def remove_refresh_token(token):
    redis = get_redis_connection()
    if redis:
        return redis.delete(f"rtoken:{token}")
    return False