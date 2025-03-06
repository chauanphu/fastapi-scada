from datetime import datetime
from bson import ObjectId
from pydantic import BaseModel, BeforeValidator
from typing import Optional, Annotated
from pydantic.fields import Field
from enum import Enum

PyObjectId = Annotated[str, BeforeValidator(str)]

# Attributes:
# - ID
# - Reason Code
# - Target: device that triggered the error, relation to 'device' collection
# - Title
# - State time: time when the error was triggered
# - End time: time when the error was resolved or null if it is still active
# - Resolved time: time when the error was resolved or null if it is still active
# - Resolved by: user who resolved the error or null if it is still active
# - Severity: critical, warning

class AlertSeverity(str, Enum):
    CRITICAL = "Nguy hiểm"
    WARNING = "Cảnh báo"
    NORMAL = "Bình thường"

class DeviceState(str, Enum):
    # Normal
    WORKING = "Thiết bị hoạt động"
    OFF = "Thiết bị tắt"
    
    # Sensor, Critical
    DISCONNECTED = "Mất kết nối"
    POWER_LOST = "Mất điện / Không đọc được công tơ"
    STILL_ON = "Thiết bị vẫn hoạt động"
    
    # Sensor, Warning
    VOLTAGE_LOW = "Điện áp thấp"
    CURRENT_HIGH = "Dòng điện cao"
    POWER_HIGH = "Công suất cao"
    POWER_FACTOR_LOW = "Hệ số công suất thấp"
    ENERGY_HIGH = "Năng lượng cao"
    ON_OUT_OF_HOUR = "Thiết bị hoạt động ngoài giờ"
    OFF_OUT_OF_HOUR = "Thiết bị tắt ngoài giờ"

class AlertModel(BaseModel):
    state: DeviceState
    device: str
    device_name: str
    timestamp: datetime
    resolved_time: Optional[datetime] | None = None
    resolved_by: Optional[str] | None = None
    severity: AlertSeverity

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}  # Ensures ObjectId is serialized to a string
    

class AlertModelFull(AlertModel):
    mac: str
    tenant_id: str

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}  # Ensures ObjectId is serialized to a string
        orm_mode = True