"""
Event Bus Service using Redis Pub/Sub for real-time communication
"""
import json
import asyncio
from typing import Any, Callable, Dict, List, Optional
from redis.asyncio import Redis
from redis.exceptions import ConnectionError, TimeoutError
from database.redis import get_async_redis_connection, get_redis_connection
from utils.logging import logger
from utils.serializers import json_serialize

class EventBus:
    def __init__(self):
        self._redis: Optional[Redis] = None
        self._subscriptions: Dict[str, List[Callable]] = {}
        self._running = False
        self._pubsub = None
    
    async def _get_redis(self) -> Redis:
        if self._redis is None:
            self._redis = await get_async_redis_connection()
        return self._redis
    
    def publish_sync(self, channel: str, message: Any) -> None:
        """
        Synchronous version of publish that can be called from non-async code
        """
        try:
            # Use the synchronous Redis connection
            redis = get_redis_connection()
            # Use custom serializer that handles datetime objects
            serialized_message = json_serialize(message) if not isinstance(message, str) else message
            redis.publish(channel, serialized_message)
        except Exception as e:
            logger.error(f"Failed to publish to channel {channel} (sync): {e}")
    
    async def subscribe(self, pattern: str, callback: Callable) -> None:
        """
        Subscribe to a channel pattern with a callback
        The callback will be called with the message data
        """
        if pattern not in self._subscriptions:
            self._subscriptions[pattern] = []
        self._subscriptions[pattern].append(callback)
        
        # Start listener if not already running
        if not self._running:
            asyncio.create_task(self._listener())
    
    async def _listener(self) -> None:
        """Listen for messages on subscribed channels"""
        self._running = True
        
        while self._running:
            try:
                redis = await self._get_redis()
                if not self._pubsub:
                    self._pubsub = redis.pubsub()
                    # Subscribe to all patterns
                    for pattern in self._subscriptions.keys():
                        await self._pubsub.psubscribe(pattern)
                
                # Process messages
                async for message in self._pubsub.listen():
                    if message["type"] in ("pmessage", "message"):
                        # Get channel/pattern
                        channel = message.get("channel", message.get("pattern", ""))
                        if isinstance(channel, bytes):
                            channel = channel.decode("utf-8")
                        
                        # Parse data
                        data = message["data"]
                        if isinstance(data, bytes):
                            data = data.decode("utf-8")
                        
                        # Find matching patterns and execute callbacks
                        for pattern, callbacks in self._subscriptions.items():
                            if (pattern.endswith("*") and channel.startswith(pattern[:-1])) or pattern == channel:
                                # Execute all callbacks for this pattern
                                for callback in callbacks:
                                    try:
                                        await callback(data, channel)
                                    except Exception as e:
                                        logger.error(f"Error in event callback: {e}")
            
            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Redis connection error in event listener: {e}. Reconnecting...")
                await asyncio.sleep(5)
                self._pubsub = None
            except Exception as e:
                logger.error(f"Unexpected error in event listener: {e}")
                await asyncio.sleep(5)
    
    async def stop(self) -> None:
        """Stop the event bus"""
        self._running = False
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
            self._pubsub = None
        
        if self._redis:
            await self._redis.close()
            self._redis = None

# Create a singleton instance
event_bus = EventBus()
