"""
Background tasks for the SCADA system.
"""
import asyncio
import time
from services.alert import check_idle_devices
from utils.logging import logger
from utils import get_real_time

async def check_idle_devices_task():
    """
    Background task to periodically check for idle devices and mark them as disconnected.
    """
    while True:
        try:
            # Check for idle devices every minute
            start_time = time.time()
            count = check_idle_devices()
            if count > 0:
                logger.info(f"Marked {count} devices as disconnected at {get_real_time().isoformat()}")
            end_time = time.time()
            
            # Calculate how long to wait before the next check
            # We want to run approximately once a minute
            execution_time = end_time - start_time
            wait_time = max(60 - execution_time, 10)  # Minimum 5 seconds between checks
            
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Error in idle device check task: {e}")
            await asyncio.sleep(60)  # Wait a minute before trying again
