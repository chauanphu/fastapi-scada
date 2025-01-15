from datetime import datetime
from enum import Enum
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field
from utils import get_real_time

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
    username: str
    action: str
    resource: str
    timestamp: datetime = get_real_time()
    role: str
    detail: str
    
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