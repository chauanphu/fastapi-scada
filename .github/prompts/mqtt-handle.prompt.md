You will handle the incoming IoT data every 5-10 seconds, received from the MQTT broker of each devices.

You will create a resilient pipeline to store, check status and cache data. Ensure that the data is consistent and non-redundant.

# MQTT data flow

1. The data is received from the MQTT client, defined in `services/mqtt.py`
2. On incoming messages, the MQTT Client will run `handle_status` function to preprocess and format incoming data
3. The preprocess data is used to:
 - Create new sensor data
 - Check for device's status
4. Update device cache
5. Create new alert record.

## Device status

For devices that has connection, based on voltage, working power, `shedule`, `toggle` and `auto`, it will classify the device state

- Every device has voltage > 0, therefore, if the voltage is 0 it means that the device cannot read the meter
- If the power is larger than the min threshold, it means the device is on physically
- If the current time is durng the schedule (noticed that the device opens during nightime till morning), it is in working hour.

For registered devices (devices have been defined in the database), that has not been responded in 1 minute since last time, it will be considered disconnected.

The device status include:
- WORKING: activated physically (power > threshold), toggle is true. If it is in auto mode then it must be during working hours.
- OFF: deactivated physically (power <= threshold), toggle is false. If it is in auto mode, it must be out of working hours.
- POWER_lOST: if voltage is 0.
- DISCONNECTED: if the device has not received signals.

## Device cache

The device data is cached in Redis. The key is `device_{mac_address}`

The cache data includes:

- `device_id`
- `device_name`
- `latitude`
- `longitude`
- `tenant_id`: Id of the tenant
- Working schedule
- Latest data from IoT
- `device_status`

For example:
```
{
  "_id": "67e0c7561e0ed75714dd1aea",
  "mac": "e465b8788700",
  "name": "H08 - Bến Chùa 1",
  "hour_on": 17,
  "hour_off": 5,
  "minute_on": 45,
  "minute_off": 31,
  "auto": false,
  "toggle": false,
  "tenant_id": "67df7a1c7faefb48db542462",
  "state": "Thiết bị hoạt động",
  "last_seen": 1742789747.806789,
  "device_id": "67e0c7561e0ed75714dd1aea",
  "timestamp": "2025-03-24T11:15:47+07:00",
  "voltage": 231.6,
  "current": 0.02,
  "power": 0.0,
  "power_factor": 0.95,
  "total_energy": 0.0,
  "energy_meter": 168.62,
  "device_name": "H08 - Bến Chùa 1",
  "latitude": 10.84177167,
  "longitude": 106.6051683
}
```