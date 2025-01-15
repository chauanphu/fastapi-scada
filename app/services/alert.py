"""
## Alert Service
This service is responsible for checking the status of the device and generating alerts based on the status.
"""

from models.report import SensorFull
from models.alert import AlertModel, DeviceState, AlertSeverity
from datetime import datetime, timedelta
import pytz
from database.mongo import get_alerts_collection
from database.redis import get_redis_connection
from utils.logging import logger

local_tz = pytz.timezone('Asia/Ho_Chi_Minh')  # Or your local timezone

class Alert:
    def __init__(self, sensor_data: SensorFull = None):
        self.sensor_data = sensor_data
        self.POWER_MINTHRESHOLD = 40
        self.current_time = datetime.now(pytz.UTC).astimezone(local_tz)

    def check_power(self):
        return self.sensor_data.power >= self.POWER_MINTHRESHOLD
    
    def in_working_hours(self):
        # Assume hour_on (18) > hour_off (5). Working in night time

        time_off = datetime(
            self.current_time.year, self.current_time.month, self.current_time.day, self.sensor_data.hour_off, self.sensor_data.minute_off,
            tzinfo=local_tz)
        # Time off is in the next day
        if self.sensor_data.hour_off < self.sensor_data.hour_on:
            time_off += timedelta(days=1)
        time_on = datetime(self.current_time.year, self.current_time.month, self.current_time.day, self.sensor_data.hour_on, self.sensor_data.minute_on,
                           tzinfo=local_tz)
        
        return time_on <= self.current_time <= time_off

    def check_status(self) -> tuple[DeviceState, AlertSeverity]:
        if self.sensor_data:
            working = self.check_power()
            on_working_hours = self.in_working_hours()
            toggle = self.sensor_data.toggle
            auto = self.sensor_data.auto
            # Normal conditions
            ## Device is on manually or automatically during working hours
            if (working and toggle) and (not auto or (auto and on_working_hours)):
                return DeviceState.WORKING, AlertSeverity.NORMAL
            ## Device is off manually or automatically when out of working hours
            elif (not working and not toggle) and (not auto or (auto and not on_working_hours)):
                return DeviceState.OFF, AlertSeverity.NORMAL
            # Critical conditions
            ## Devie is lost power
            elif not working and toggle:
                return DeviceState.POWER_LOST, AlertSeverity.CRITICAL
            ## Device is still on despite switching down
            elif working and not toggle:
                print(f"working: {working}, toggle: {toggle}")
                return DeviceState.WORKING, AlertSeverity.CRITICAL
            # Warning conditions
            ## Device is on out of working hours
            elif working and auto and not on_working_hours:
                return DeviceState.ON_OUT_OF_HOUR, AlertSeverity.WARNING
            ## Device is off out of working hours
            elif not working and auto and on_working_hours:
                return DeviceState.OFF_OUT_OF_HOUR, AlertSeverity.WARNING
        else: 
            return DeviceState.DiSCONNECTED, AlertSeverity.CRITICAL
        
def get_cached_alert(device_id: str) -> str:
    redis = get_redis_connection()
    cached_alert = redis.get("state:" + device_id) # Get UTF-8 string
    return cached_alert.decode("utf-8") if cached_alert else ""

def increase_alert_count(device_id: str):
    redis = get_redis_connection()
    response = redis.incr("alert_count:" + device_id)
    redis.publish("alert", f"{device_id}:{response}")

# Pub/sub latest alert message
def subscribe_alert():
    redis = get_redis_connection()
    pubsub = redis.pubsub()
    pubsub.subscribe("alert:*")
    return pubsub

def publish_alert(message: AlertModel, tenant_id: str):
    redis = get_redis_connection()
    redis.publish("alert:" + tenant_id, message.model_dump_json())

def reset_alert_count(device_id: str):
    redis = get_redis_connection()
    redis.set("alert_count:" + device_id, 0)

def process_data(data: SensorFull, tenant_id: str):
    try:
        alert = Alert(data)
        state, severity = alert.check_status()
        if severity == AlertSeverity.NORMAL:
            return
        current_state = get_cached_alert(data.device_id)
        # If the current state is not the same as the new state, update the alert
        if current_state != state.name or not current_state:
            new_alert = AlertModel(
                state=state,
                device=data.device_id,
                device_name=data.device_name,
                timestamp=alert.current_time,
                severity=severity
            )
            alert_collection = get_alerts_collection(tenant_id)
            alert_collection.insert_one(new_alert.model_dump())
            # Cache the new state
            redis = get_redis_connection()
            redis.set("state:" + data.device_id, state.name)
            publish_alert(new_alert)

    except Exception as e:
        logger.error(f"Failed to process alert data: {e}")
        return