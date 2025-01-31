from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr

from models.auth import Role
from pydantic import model_validator

from models.tenant import Tenant

class User(BaseModel):
  id: Optional[ObjectId] | Optional[str] = Field(alias="_id", default=None)  
  username: str | None = None  
  email: EmailStr | None = None
  role: Role | None = None  
  disabled: bool| None = False  
  tenant: Tenant | None = None
  
  class Config:
    populate_by_name = True
    arbitrary_types_allowed = True
    json_encoders = {ObjectId: str}  # Ensures ObjectId is serialized to a string

class OnCreateUser(BaseModel):
  username: str = None  
  email: EmailStr = None
  role: Role = None  
  disabled: Optional[bool] = False
  password: str = None
  tenant_id: Optional[str] = None

class AccountCreate(OnCreateUser):
  @model_validator(mode='after')
  def check_tenant_id(cls, model):
    if model.role != Role.SUPERADMIN and model.tenant_id is None:
      raise ValueError('tenant_id cannot be None if role is not SUPERADMIN')
    return model
  
  # Overwrite model_dump to encode the role as a string
  def model_dump(self):
    model = super().model_dump()
    model['role'] = self.role.value
    return model

class AccountEdit(BaseModel):
  username: str | None = None  
  email: EmailStr | None = None
  role: Role | None = None  
  disabled: bool| None = False
  tenant_id: str | None = None

  @model_validator(mode='after')
  def check_tenant_id(cls, model):
    if model.role != Role.SUPERADMIN and model.tenant_id is None:
      raise ValueError('tenant_id cannot be None if role is not SUPERADMIN')
    return model