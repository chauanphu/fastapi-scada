from typing import Annotated, Optional
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from models.auth import User

from models.device import Device
from utils.auth import Role, RoleChecker
from crud.firmware import add_new_firmware, get_firmware_by_version, get_latest_firmware, get_all_metadata as crud_get_all_metadata
from crud.device import read_device
from utils.logging import logger
from services.mqtt import client

router = APIRouter(
    prefix="/firmware",
    tags=["firmware"]
)

# Upload firmware
@router.post("/upload/")
async def upload_firmware(
    current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.SUPERADMIN]))],
    file: UploadFile = File(...), 
    version: str = "0.1.0",
):
    # Check file extension
    if not file.filename.endswith('.bin'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .bin files are allowed."
        )

    # 1. Read file in memory
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Empty file."
        )

    add_new_firmware(contents, version, file.filename)

    # 5. Return info to the user
    return status.HTTP_201_CREATED

# Get latest firmware
@router.get("/")
async def download_firmware(version: Optional[str] = None):
    if not version or version == "latest":
        file = get_latest_firmware()
    else:
        file = get_firmware_by_version(version)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No firmware found."
        )
    headers = {"Content-Disposition": f"attachment; filename={file.filename}"}
    if "hash_value" in file.metadata:
        headers["X-Checksum"] = file.metadata["hash_value"]
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Firmware metadata is missing hash value."
        )
    if "version" in file.metadata:
        headers["X-Version"] = file.metadata["version"]
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Firmware metadata is missing version."
        )
    return Response(content=file.read(), media_type="application/octet-stream", headers=headers)

# Get all firmware metadata
@router.get("/metadata/")
async def get_all_metadata(current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.SUPERADMIN]))]):
    try:
        metadata = crud_get_all_metadata()
        return metadata
    except Exception as e:
        logger.error(f"Failed to get firmware metadata: {e}")
        raise HTTPException(status_code=500, detail="Failed to get firmware metadata")

# Update device
@router.put("/update/{device_id}")
async def update_device(
    current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.SUPERADMIN]))],
    device_id: str,
    version: Optional[str] = None
):
    try:
        device: Device = read_device(device_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found."
            )
        client.update_device(device.mac, version)
        return status.HTTP_200_OK
    except Exception as e:
        logger.error(f"Failed to update device: {e}")
        raise HTTPException(status_code=500, detail="Failed to update device")
    
# Mass update devices
@router.put("/update/")
async def mass_update_devices(
    current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.SUPERADMIN]))],
    version: Optional[str] = None
):
    try:
        client.update_all(version)
        return status.HTTP_200_OK
    except Exception as e:
        logger.error(f"Failed to update devices: {e}")
        raise HTTPException(status_code=500, detail="Failed to update devices")