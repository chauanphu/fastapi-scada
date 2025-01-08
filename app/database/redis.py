from redis import Redis
from redis.exceptions import ConnectionError

from utils.config import REDIS_HOST, REDIS_PORT
from utils.logging import logger

def get_redis_connection():
    try:
        redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=0, retry_on_error=5)
        return redis
    except ConnectionError:
        logger.error(f"Unable to connect to Redis server at {REDIS_HOST}:{REDIS_PORT}")
        return None
    
# Add a refresh token into Redis list with expiration time
def set_refresh_token(token):
    redis = get_redis_connection()
    if redis:
        redis.set("refresh_token", token)
        return True
    return False

# Check if the refresh token exists in the Redis list
def check_refresh_token(token):
    redis = get_redis_connection()
    if redis:
        return redis.exists(token)
    return False

# Remove the refresh token from the Redis list
def remove_refresh_token(token):
    redis = get_redis_connection()
    if redis:
        return redis.delete(token)
    return False