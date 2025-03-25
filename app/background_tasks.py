"""
Background tasks for the SCADA system.
"""
import asyncio
import time
from services.alert import check_idle_devices
from utils.logging import logger
from utils import get_real_time
from services.event_bus import event_bus

async def check_idle_devices_task():
    """
    Background task to periodically check for idle devices and mark them as disconnected.
    """
    while True:
        try:
            # Check for idle devices every minute
            start_time = time.time()
            count, dis_devices = check_idle_devices()
            if count > 0:
                logger.info(f"Marked {count} devices as disconnected at {get_real_time().isoformat()}")
            for device in dis_devices:
                tenant_id, device_data = device
                logger.debug(f"Publishing device status update for tenant {tenant_id}")
                event_bus.publish_sync(f"device_status:{tenant_id}", device_data)
            end_time = time.time()
            
            execution_time = end_time - start_time
            wait_time = max(60 - execution_time, 10)  # Minimum 5 seconds between checks
            
            await asyncio.sleep(wait_time)
        except Exception as e:
            logger.error(f"Error in idle device check task: {e}")
            await asyncio.sleep(60)  # Wait a minute before trying again
