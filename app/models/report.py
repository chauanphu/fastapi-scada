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
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    mac: str
    timestamp: datetime
    voltage: float
    current: float
    power: float
    power_factor: float
    total_energy: float

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}  # Ensures ObjectId is serialized to a string

class SensorDataBase(BaseModel):
    timestamp: datetime
    voltage: float
    current: float
    power: float
    power_factor: float
    total_energy: float
    mac: str