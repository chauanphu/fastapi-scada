from datetime import timedelta
from redis import Redis
from redis.exceptions import ConnectionError

def get_redis_connection():
    try:
        redis = Redis()
        return redis
    except ConnectionError:
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