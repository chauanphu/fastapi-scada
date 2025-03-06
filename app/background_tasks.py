"""
Background tasks for the SCADA system.
"""
import asyncio
import time
from datetime import datetime
from services.cache_service import cache_service
from models.alert import DeviceState
from utils.logging import logger

async def check_idle_devices_task():
    """
    Background task to periodically check for idle devices and mark them as disconnected.
    """
    while True:
        try:
            # Check for idle devices every minute
            start_time = time.time()
            count = cache_service.check_idle_devices()
            if count > 0:
                logger.info(f"Marked {count} devices as disconnected at {datetime.now()}")
            end_time = time.time()
            
            # Calculate how long to wait before the next check
            # We want to run approximately once a minute
            wait_time = max(60 - (end_time - start_time), 0)
            
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Error in idle device check task: {e}")
            await asyncio.sleep(60)  # Wait a minute before trying again
