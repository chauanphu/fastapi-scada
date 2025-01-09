from typing import Optional

from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr

from models.auth import Role

class User(BaseModel):
  id: Optional[ObjectId] | Optional[str] = Field(alias="_id", default=None)  
  username: str | None = None  
  email: EmailStr | None = None
  role: Role | None = None  
  disabled: bool| None = False  

  class Config:
    populate_by_name = True
    arbitrary_types_allowed = True
    json_encoders = {ObjectId: str}  # Ensures ObjectId is serialized to a string

class AccountCreate(BaseModel):
  username: str | None = None  
  email: EmailStr | None = None
  role: Role | None = None  
  disabled: bool| None = False  
  password: str | None = None


class AccountEdit(BaseModel):
  username: str | None = None  
  email: EmailStr | None = None
  role: Role | None = None  
  disabled: bool| None = False  