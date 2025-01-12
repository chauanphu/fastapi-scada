import os
from typing import Annotated
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from models.auth import User

from utils.auth import Role, RoleChecker
from crud.firmware import add_new_firmware, get_latest_firmware
from utils.logging import logger
router = APIRouter(
    prefix="/firmware",
    tags=["firmware"]
)

# Upload firmware
@router.post("/upload/")
async def upload_firmware(
    current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.SUPERADMIN], isLogged=False))],
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
@router.get("/latest/")
async def get_latest():
    file = get_latest_firmware()
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

# Update device
@router.put("/update/{device_id}")
async def update_device(
    current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.SUPERADMIN], isLogged=False))],
    device_id: str,
    version: str,
):
    pass

# Mass update devices
@router.put("/update/")
async def mass_update_devices(
    current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.SUPERADMIN], isLogged=False))],
    version: str,
):
    pass

