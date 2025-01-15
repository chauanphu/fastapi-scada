from datetime import datetime
from enum import Enum
from typing import Optional
from bson import ObjectId
from fastapi.params import Query
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
    username: Optional[str] | None = None,
    action: Optional[Action] | None = None,
    resource: Optional[str] | None = None,
    start: datetime | None = Query(None, example="2022-01-01T00:00:00"),
    end: datetime | None = Query(None, example="2022-12-31T23:59:59")