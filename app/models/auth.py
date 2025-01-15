from enum import Enum
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field, model_validator  

class Role(Enum):  
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    MONITOR = "monitor"
    OPERATOR = "operator"

class TokenData(BaseModel):
    username: str
    tenant_id: str
    roles: list[str]

class User(BaseModel):
  id: ObjectId | str = Field(alias="_id", default=None)  
  username: str
  tenant_id: Optional[str] = None
  email: str
  role: Role
  disabled: bool
  hashed_password: str

  @model_validator(mode='after')
  def check_tenant_id(cls, model):
    if model.role != Role.SUPERADMIN and model.tenant_id is None:
      raise ValueError('tenant_id cannot be None if role is not SUPERADMIN')
    return model
  
  class Config:
    populate_by_name = True
    arbitrary_types_allowed = True
    json_encoders = {ObjectId: str}  # Ensures ObjectId is serialized to a string
  
class Token(BaseModel):  
  access_token: str | None = None  
  refresh_token: str | None = None
  tenant_id: str | None = None