from models.auth import Role

UserSchema = {
    "$jsonSchema": {
    "bsonType": "object",
    "required": ["username", "hashed_password", "email", "role", "disabled"],
    "properties": {
        "username": {
            "bsonType": "string",
            "description": "Username of the user"
        },
        "hashed_password": {
            "bsonType": "string",
            "description": "Hashed password of the user"
        },
        "email": {
            "bsonType": "string",
            "description": "Email of the user"
        },
        
        "role": {
            "enum": [role.value for role in Role],
            "description": "Role of the user"
        },
    }
    }
}