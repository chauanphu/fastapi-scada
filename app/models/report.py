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
    timestamp: datetime
    voltage: float
    current: float
    power: float
    power_factor: float
    total_energy: float
    hour_on: int
    hour_off: int
    minute_on: int
    minute_off: int
    device_id: str
    toggle: bool
    auto: bool