The caching system will store the current information about devices in Redis to increase performance and consistency

## Key-value

The key is `device_{mac_address}`

The cache data includes:

- General information: This data is avaiable and not often updated
 - `_id`: device's id
 - `name`: device name
 - `tenant_id`: Id of tenant

- Control settings: This data is available since created and often updated by user
 - `toggle` (boolean) : physically activated or not
 - `auto` (boolean): in auto mode or not
 - `hour_on`: int (0-23)
 - `minute_on`: int (0-59)
 - `hour_off`: int (0-23)
 - `minute_off`: int (0-59)

- Realtime data (Optional): This data only available if receive from MQTT
 - `voltage`: float
 - `current`: float
 - `power`: float
 - `power_factor`: float
 - `total_energy`: float
 - `energy_meter`: float
 - `state`: enum

 ## Requirements
 
- A function to get device cache based on mac address, fallback to query database if not exists
- A function to update the control settings: for `crud/device.py`
- A function to update realtime data: for `crud/report.py`
- A function to update state: `service/alert.py`
- Initially, general information and control settings should be cached.

**Partial update is recommended** if it simplifies the process.

Ensure SOLID principles, consistency and resilient.