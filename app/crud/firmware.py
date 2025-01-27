import hashlib

from gridfs import GridFS
from gridfs.errors import NoFile
from gridfs.grid_file import GridOut
from database.mongo import get_fs
from models.firmware import MetaData
from datetime import datetime
import pytz

def add_new_firmware(contents, version, file_name) -> tuple[str, str]:
    # 2. Calculate hash (SHA-256 as an example)
    hash_val = hashlib.sha256(contents).hexdigest()
    current_time = datetime.now(pytz.utc)
    # 3. Store metadata in the DB
    new_firmware = MetaData(version=version, hash_value=hash_val, upload_time=current_time)
    fs = get_fs()
    file_id = fs.put(contents, filename=file_name, metadata=new_firmware.model_dump())
    return file_id, hash_val

def get_latest_firmware() -> GridOut:
    # 1. Get the latest firmware metadata
    fs = get_fs()
    latest_file = fs.find().sort("uploadDate", -1).limit(1)
    # Convert to a list to access the file object (or iterate directly)
    latest_file = list(latest_file)
    if latest_file:
        file = latest_file[0]
        file = fs.get(file._id)
        return file
    return None
    
def get_firmware(file_id) -> tuple[bytes, str, dict]:
    try:
        fs = get_fs()
        # Retrieve the file by its ID
        grid_out = fs.get(file_id)
        # Read the contents (or stream them as needed)
        file_data = grid_out.read()
        # Return both file data and metadata
        return file_data, grid_out.filename, grid_out.metadata
    except NoFile:
        return None, None, None

def get_all_metadata() -> list[MetaData]:
    """
    Get all firmware metadata, regardless of the tenant.
    """
    fs = get_fs()
    metadata = fs.find()
    return [MetaData.model_validate(file.metadata) for file in metadata]