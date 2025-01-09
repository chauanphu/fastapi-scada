from enum import Enum
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field  

class Role(Enum):  
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    MONITOR = "monitor"
    OPERATOR = "operator"

class User(BaseModel):
  id: ObjectId | str = Field(alias="_id", default=None)  
  username: str
  email: str
  role: Role
  disabled: bool
  hashed_password: str

  class Config:
    populate_by_name = True
    arbitrary_types_allowed = True
    json_encoders = {ObjectId: str}  # Ensures ObjectId is serialized to a string
  
class Token(BaseModel):  
  access_token: str | None = None  
  refresh_token: str | None = None