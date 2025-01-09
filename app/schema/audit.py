AuditSchema = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": ["username", "action", "timestamp"],
        "properties": {
            "username": {
                "bsonType": "string",
                "description": "Username of the user who performed the action"
            },
            "action": {
                "bsonType": "string",
                "description": "Action performed by the user"
            },
            "timestamp": {
                "bsonType": "date",
                "description": "Timestamp of the action"
            }
        }
    }
}