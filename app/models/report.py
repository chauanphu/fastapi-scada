from pydantic import BaseModel, BeforeValidator
from datetime import datetime
from typing import Optional, Annotated
from pydantic.fields import Field
from bson import ObjectId

from datetime import datetime

PyObjectId = Annotated[str, BeforeValidator(str)]
class EnergyReportResponse(BaseModel):
    timestamp: datetime
    total_energy: float

class SensorModel(BaseModel):
    mac: str
    device_id: str
    timestamp: datetime
    voltage: float
    current: float
    power: float
    power_factor: float
    total_energy: float
    energy_meter: float
    toggle: bool

class SensorFull(SensorModel):
    device_name: str
    toggle: bool
    auto: bool
    hour_on: int
    hour_off: int
    minute_on: int
    minute_off: int
    auto: bool
    latitude: float
    longitude: float
    tenant_id: str
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}  # Ensures ObjectId is serialized to a string