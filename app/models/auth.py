from enum import Enum
from typing import Optional
from bson import ObjectId
from pydantic import BaseModel, Field  

class Role(Enum):  
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    MONITOR = "monitor"
    OPERATOR = "operator"
    
class Action(Enum):
    LOGIN = "login"
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    UPDATE = "update"
    COMMAND = "command"
    MONITOR = "monitor"

class User(BaseModel):
  id: Optional[ObjectId] | Optional[str] = Field(alias="_id", default=None)  
  username: str | None = None  
  email: str | None = None  
  role: Role | None = None  
  disabled: bool| None = None  
  hashed_password: str | None = None  

  class Config:
    populate_by_name = True
    arbitrary_types_allowed = True
    json_encoders = {ObjectId: str}  # Ensures ObjectId is serialized to a string
  
class Token(BaseModel):  
  access_token: str | None = None  
  refresh_token: str | None = None