from datetime import datetime
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field

class Tenant(BaseModel):
  id: Optional[ObjectId] | Optional[str] = Field(alias="_id", default=None)  
  name: str
  created_date: datetime
  disabled: bool

  class Config:
    populate_by_name = True
    arbitrary_types_allowed = True
    json_encoders = {ObjectId: str}  # Ensures ObjectId is serialized to a string

class TenantCreate(BaseModel):
  name: str
  created_date: datetime = Field(default_factory=datetime.now)
  disabled: bool = False