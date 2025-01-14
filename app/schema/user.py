from models.auth import Role
# Import Pymongo Validation Schema

UserSchema = {
    "$jsonSchema": {
    "bsonType": "object",
    "required": ["username", "hashed_password", "email", "role", "disabled"],
    "properties": {
        "username": {
            "bsonType": "string",
            "description": "Username of the user",
            "uniqueItems": True
        },
        "tenant_id": {
            "bsonType": "string",
            "description": "Tenant ID"
        },
        "hashed_password": {
            "bsonType": "string",
            "description": "Hashed password of the user"
        },
        "email": {
            "bsonType": "string",
            "pattern": "^.+@.+\..+$",
            "description": "Email of the user",
            "uniqueItems": True
        },
        "role": {
            "enum": [role.value for role in Role],
            "description": "Role of the user"
        },
    }
    }
}