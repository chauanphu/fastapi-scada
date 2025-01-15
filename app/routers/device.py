from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from crud.audit import append_audit_log
from crud.device import create_device, read_devices, configure_device, delete_device, update_device
from utils.auth import Role, RoleChecker
from models.audit import Action, AuditLog
from models.device import Device, DeviceCreate, DeviceConfigure, DeviceEdit, Schedule
from models.auth import User
from services.mqtt import client
from utils.logging import logger

router = APIRouter(
    prefix="/devices",
    tags=["devices"]
)

@router.get("/", response_model=list[Device])
def get_devices(current_user: Annotated[User, Depends(RoleChecker(allowed_roles="*"))]):
    if current_user.role == Role.SUPERADMIN:
        results = read_devices()
    else:
        results = read_devices(tenant_id=current_user.tenant_id)
    return results

@router.post("/")
def create_new_device(
    current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.SUPERADMIN]))], 
    device: DeviceCreate):
    try:
        # Reject if attempt of a non-superadmin to create a superadmin
        if current_user.role != Role.SUPERADMIN:
            raise HTTPException(status_code=401, detail="Only superadmin can create device")
        create_device(device)
        return status.HTTP_201_CREATED
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to create device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{device_id}")
def put_device(_: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.SUPERADMIN]))],
    device_id: str, 
    device: DeviceEdit
    ):
    result = update_device(device_id, device)
    if result:
        return status.HTTP_200_OK
    raise HTTPException(status_code=400, detail="Failed to update device")

@router.put("/toggle/{device_id}")
def toggle(current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN, Role.OPERATOR]))],
           device_id: str, 
           value: bool):
    try:
        command = DeviceConfigure(auto=False, toggle=value)
        result = configure_device(current_user=current_user, device_id=device_id, device=command)
        if not result:
            raise HTTPException(status_code=400, detail="Failed to toggle device")
        client.toggle_device(result.mac, value)
        template_log = AuditLog(
            username=current_user.username,
            action=Action.COMMAND,
            resource="thiết bị",
            role=current_user.role,
            detail=f"{"Bật" if value else "Tắt"} thiết bị {result.name}"
        )
        append_audit_log(template_log, role=current_user.role, tenant_id=current_user.tenant_id)
        return status.HTTP_200_OK
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to toggle device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/auto/{device_id}")
def auto(current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN, Role.OPERATOR]))],
            device_id: str, 
            value: bool):
    try:
        command = DeviceConfigure(auto=value)
        result: Device = configure_device(current_user=current_user, device_id=device_id, device=command)
        if not result:
            raise HTTPException(status_code=400, detail="Failed to toggle device")
        client.set_auto(result.mac, value)
        template_log = AuditLog(
            username=current_user.username,
            action=Action.COMMAND,
            resource="thiết bị",
            role=current_user.role,
            detail=f"{"Bật" if value else "Tắt"} chế độ tự động cho thiết bị {result.name}"
        )
        append_audit_log(template_log, role=current_user.role, tenant_id=current_user.tenant_id)
        return status.HTTP_200_OK
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to change auto mode of device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/schedule/{device_id}")
def schedule(current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN, Role.OPERATOR]))],
            device_id: str, 
            value: Schedule):
    try:
        command = DeviceConfigure(**value.model_dump())
        result = configure_device(current_user=current_user, device_id=device_id, device=command)
        if not result:
            raise HTTPException(status_code=400, detail="Failed to toggle device")
        client.set_schedule(result.mac, value)
        template_log = AuditLog(
            username=current_user.username,
            action=Action.COMMAND,
            resource="thiết bị",
            role=current_user.role,
            detail=f"Đặt lịch cho thiết bị {result.name}"
        )
        append_audit_log(template_log, role=current_user.role)
        return status.HTTP_200_OK
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to set schedule for device: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{device_id}")
def delete(
    _: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.SUPERADMIN]))],
    device_id: str):
    
    result = delete_device(device_id)
    if result:
        return status.HTTP_200_OK
    raise HTTPException(status_code=400, detail="Failed to delete device")