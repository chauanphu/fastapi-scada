
from datetime import datetime
from pydantic import BaseModel

class MetaData(BaseModel):
    version: str
    hash_value: str
    upload_time: datetime