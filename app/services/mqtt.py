import math
import pytz
from models.device import Schedule
from utils.config import MQTT_BROKER, MQTT_PORT, DEBUG
import re
import json
import random
from datetime import datetime
import json
from paho.mqtt import client as mqtt_client
from crud.report import create_sensor_data
from utils.logging import logger

local_tz = pytz.timezone('Asia/Ho_Chi_Minh')  # Or your local timezone

def get_tz_datetime(timestamp: int | None = None) -> int:
    if not timestamp:
        # Get current time
        return datetime.now(pytz.UTC).astimezone(local_tz)
    else:   
        utc_dt = datetime.fromtimestamp(timestamp, pytz.UTC)
        time = utc_dt.replace(tzinfo=pytz.FixedOffset(420)) # UTC+7
        return time.astimezone(local_tz)
    
class Client(mqtt_client.Client):
    def __init__(self):
        self.ID = "monitoring-" + str(random.randint(100, 999))
        super().__init__(mqtt_client.CallbackAPIVersion.VERSION2, client_id=self.ID)
        self.HOST = MQTT_BROKER
        self.PORT = MQTT_PORT
        # self.ID = "monitoring-service" + str(random.randint(0, 1000))
        logger.info(f"Connecting to MQTT Broker: {self.HOST}:{self.PORT}")
        self.ttl = 60 * 5 # 5 minutes

    def connect(self, keepalive=60):
        super().connect(self.HOST, self.PORT, keepalive)

    def handle_status(self, mac, payload: dict):
        # Validate and parse data
        try:
            # Parse int "time" to datetime object "timestamp"
            payload["timestamp"] = get_tz_datetime(payload["time"])
            payload.pop("time")
            payload["mac"] = mac
            payload["energy_meter"] = payload["total_energy"]
            payload["power_factor"] = round(random.uniform(0.95, 0.97), 2)
            
            if payload["voltage"] == 0.0:
                # Mock data
                payload["voltage"] = round(random.uniform(230, 240), 1)
                if payload["toggle"]:   
                    payload["current"] = round(random.uniform(1.2, 1.4), 1)
                    payload["power"] = math.ceil(random.uniform(330, 340))
                else:
                    payload["current"] = round(random.uniform(0.1, 0.3), 1)
                    payload["power"] = math.ceil(random.uniform(0, 5))
                    
            payload["total_energy"] = (payload["power"] / 1000 / 360) * payload["power_factor"]

            # Insert data to MongoDB
            create_sensor_data(payload)

        except Exception as e:
            logger.error(f"Failed to parse data from {mac}: {e}")
            return 

    def handle_connection(self, mac: str, payload):
        pass

    def toggle_device(self, mac, state: bool):
        topic = f"unit/{mac}/command"
        body = {
            "command": "TOGGLE",
            "payload": "on" if state else "off"
        }
        if DEBUG:
            print("Topic", topic)
            print("Body", body)
        else:
            self.publish(topic, json.dumps(body))

    def set_auto(self, mac, state: bool):
        topic = f"unit/{mac}/command"
        body = {
            "command": "AUTO",
            "payload": "on" if state else "off"
        }
        if DEBUG:
            print("Topic", topic)
            print("Body", body)
        else:
            self.publish(topic, json.dumps(body))

    def set_schedule(self, mac, schedule: Schedule):
        topic = f"unit/{mac}/command"
        body = {
            "command": "SCHEDULE",
            "payload": schedule.model_dump()
        }
        if DEBUG:
            print("Topic", topic)
            print("Body", body)
        else:
            self.publish(topic, json.dumps(body))

    # Update all device
    def update_all(self, version: str):
        topic = "firmware/update"
        body = {
            "version": version if version else "latest"
        }
        if DEBUG:
            print("Topic", topic)
            print("Body", body)
        else:
            self.publish(topic, json.dumps(body))

    # Update a device
    def update_device(self, mac: str, version: str):
        topic = f"unit/{mac}/update"
        body = {
            "version": version if version else "latest"
        }
        if DEBUG:
            print("Topic", topic)
            print("Body", body)
        else:
            self.publish(topic, json.dumps(body))

    ## Override
    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        logger.info(f"Connected with result code {reason_code}")
        self.subscribe("unit/+/status")
        self.subscribe("unit/+/alive")

    def on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        logger.info(f"Disconnected with result code {reason_code}")

    def on_message(self, client, userdata, message):
        try:
            topic = message.topic
            match = re.match(r"unit/(\w+)/(status|alive)", topic)
            if match:
                mac_address, _type = match.groups()
                body = message.payload.decode("utf-8")
                if _type == "status":
                    payload = json.loads(body)
                    self.handle_status(mac_address, payload)
                elif _type == "alive":
                    payload = json.loads(body)
                    self.handle_connection(mac_address, payload)
            else:
                logger.error(f"Unknown topic: {topic}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {e}")
        except KeyError as e:
            logger.error(f"Missing key: {e}")
        except Exception as e:
            logger.error(f"Error: {e}")


client = Client()