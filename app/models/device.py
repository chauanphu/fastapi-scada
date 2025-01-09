from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field

class Device(BaseModel):
  id: Optional[ObjectId] | Optional[str] = Field(alias="_id", default=None)  
  mac: str | None = None
  name: str | None = None
  hour_on: int | None = None
  hour_off: int | None = None
  minute_on: int | None = None
  minute_off: int | None = None
  auto: bool | None = None
  toggle: bool | None = None

  class Config:
    populate_by_name = True
    arbitrary_types_allowed = True
    json_encoders = {ObjectId: str}  # Ensures ObjectId is serialized to a string

class DeviceCreate(BaseModel):
    mac: str
    name: str
    hour_on: int
    hour_off: int
    minute_on: int
    minute_off: int
    auto: bool = False
    toggle: bool = False

class DeviceConfigure(BaseModel):
    hour_on: int | None = None
    hour_off: int | None = None
    minute_on: int | None = None
    minute_off: int | None = None
    auto: bool | None = None
    toggle: bool | None = None

class DeviceEdit(BaseModel):
    mac: Optional[str] = None
    name: Optional[str] = None