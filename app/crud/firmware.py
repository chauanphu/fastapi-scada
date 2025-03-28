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

def check_firmware_exists(contents) -> bool:
    # 2. Calculate hash (SHA-256 as an example)
    hash_val = hashlib.sha256(contents).hexdigest()
    # 3. Check if the hash exists in the DB
    fs = get_fs()
    file = fs.find_one({"metadata.hash_value": hash_val})
    return file is not None

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
    
# Get file by version
def get_firmware_by_version(version: str) -> GridOut:
    fs = get_fs()
    try:
        file = fs.find_one({"metadata.version": version})
        return file
    except NoFile:
        return None

def get_all_metadata() -> list[MetaData]:
    """
    Get all firmware metadata, regardless of the tenant.
    """
    fs = get_fs()
    metadata = fs.find()
    return [MetaData.model_validate(file.metadata) for file in metadata]

def delete_firmware_by_version(version: str) -> bool:
    """
    Delete a firmware by its version.
    Returns True if the firmware was deleted, False if it wasn't found.
    """
    fs = get_fs()
    result = fs.find_one({"metadata.version": version})
    if result:
        file_id = result._id
        fs.delete(file_id)
        return True
    return False