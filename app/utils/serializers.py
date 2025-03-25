"""
Utilities for serializing complex objects to JSON
"""
import json
from datetime import datetime, date
from fastapi.encoders import jsonable_encoder
from typing import Any

class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that can handle datetime objects"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

def json_serialize(obj: Any) -> str:
    """
    Serialize an object to JSON string, handling datetime objects.
    Uses FastAPI's jsonable_encoder to handle model objects as well.
    
    Args:
        obj: The object to serialize to JSON
        
    Returns:
        JSON string representation of the object
    """
    # First convert models to dict with FastAPI's encoder
    encodable_obj = jsonable_encoder(obj)
    # Then serialize to JSON string with our custom encoder
    return json.dumps(encodable_obj, cls=DateTimeEncoder)
