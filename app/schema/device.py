# name, mac, hour_on: int, hour_off: int, minute: on, minute_off: int, toggle: bool, auto: bool
DeviceSchema = {
    "$jsonSchema": {
    "bsonType": "object",
    "required": ["name", "mac", "hour_on", "hour_off", "minute_on", "minute_off", "toggle", "auto", "tenant_id"],
    "properties": {
        "name": {
            "bsonType": "string",
            "description": "Device name",
            "uniqueItems": True
        },
        "mac": {
            "bsonType": "string",
            "description": "MAC address of the device",
            "uniqueItems": True
        },
        "tenant_id": {
            "bsonType": "string",
            "description": "Tenant ID"
        },
        "hour_on": {
            "bsonType": "int",
            "description": "Hour to turn on the device"
        },
        "hour_off": {
            "bsonType": "int",
            "description": "Hour to turn off the device"
        },
        "minute_on": {
            "bsonType": "int",
            "description": "Minute to turn on the device"
        },
        "minute_off": {
            "bsonType": "int",
            "description": "Minute to turn off the device"
        },
        "toggle": {
            "bsonType": "bool",
            "description": "Toggle the device"
        },
        "auto": {
            "bsonType": "bool",
            "description": "Auto mode"
        }
    }
    }
}

SensorSchema = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["name", "mac", "voltage", "current", "power", "power_factor", "total_energy", "toggle"],
        "properties": {
            "name": {
                "bsonType": "string",
                "description": "Device name",
            },
            "mac": {
                "bsonType": "string",
                "description": "MAC address of the device",
            },
            "voltage": {
                "bsonType": "float",
                "description": "Voltage"
            },
            "current": {
                "bsonType": "float",
                "description": "Current"
            },
            "power": {
                "bsonType": "float",
                "description": "Power"
            },
            "power_factor": {
                "bsonType": "float",
                "description": "Power factor"
            },
            "total_energy": {
                "bsonType": "float",
                "description": "Total energy"
            },
            "toggle": {
                "bsonType": "bool",
                "description": "Toggle the device"
            }
        }
    }
}