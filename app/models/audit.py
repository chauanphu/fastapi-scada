from datetime import datetime
from enum import Enum
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field

class Action(Enum):
    LOGIN = "đăng nhập"
    READ = "đọc"
    WRITE = "thêm"
    DELETE = "xóa"
    UPDATE = "cập nhật"
    COMMAND = "điều khiển"
    MONITOR = "theo dõi"

class AuditLog(BaseModel):
    id: Optional[ObjectId] | Optional[str] = Field(alias="_id", default=None)  
    username: str | None = None
    action: str | None = None
    resource: str | None = None
    timestamp: datetime | None = None
    role: str | None = None
    detail: str | None = None
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}  # Ensures ObjectId is serialized to a string

class AuditQuery(BaseModel):
    username: str | None = None
    action: str | None = None
    resource: str | None = None
    start: datetime | None = None
    end: datetime | None = None