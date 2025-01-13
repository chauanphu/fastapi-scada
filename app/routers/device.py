import json
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

# from crud.user import read_users, create_user, update_user, delete_user
from crud.audit import append_audit_log
from crud.device import create_device, read_devices, configure_device, delete_device, update_device
from utils.auth import Role, RoleChecker
from models.audit import Action, AuditLog
from models.device import Device, DeviceCreate, DeviceConfigure, DeviceEdit, Schedule
from models.auth import User
from services.mqtt import client

router = APIRouter(
    prefix="/devices",
    tags=["devices"]
)

@router.get("/", response_model=list[Device])
def get_devices(current_user: Annotated[
    User, Depends(
    RoleChecker(allowed_roles="*"))
    ]):
    results = read_devices()
    log = AuditLog(
        username=current_user.username,
        action=Action.READ,
        resource="thiết bị",
        detail=f"Xem danh sách thiết bị"
    )
    append_audit_log(log, role=current_user.role)
    return results

@router.post("/", response_model=Device)
def create_new_device(
    current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN],isLogged=False))], 
    device: DeviceCreate):
    new_device = create_device(device)
    if new_device:
        append_audit_log(AuditLog(
            username=current_user.username,
            action=Action.WRITE,
            resource="thiết bị",
            detail=f"Tạo thiết bị {new_device.name}"
        ), role=current_user.role)
        return new_device
    raise HTTPException(status_code=400, detail="Failed to create device")

@router.put("/{device_id}")
def put_device(current_user: Annotated[
    User, Depends(
    RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN],
                action=Action.UPDATE,
                resource="tài khoản"))
    ]
    ,
    device_id: str, 
    device: DeviceEdit
    ):
    result = update_device(device_id, device)

    if result:
        result = Device(**result)
        append_audit_log(AuditLog(
            username=current_user.username,
            action=Action.UPDATE,
            resource="thiết bị",
            detail=f"Cập nhật thông tin thiết bị {result["name"]}"
        ), role=current_user.role)

        return status.HTTP_200_OK
    raise HTTPException(status_code=400, detail="Failed to update device")

@router.put("/toggle/{device_id}")
def toggle(current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN, Role.OPERATOR], isLogged=False))],
            device_id: str, 
            value: bool):
    command = DeviceConfigure(toggle=value)
    result = configure_device(device_id, command)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to toggle device")
    client.toggle_device(result["mac"], value)
    template_log = AuditLog(
        username=current_user.username,
        action=Action.COMMAND,
        resource="thiết bị",
        detail=f"{"Bật" if value else "Tắt"} thiết bị {result["name"]}"
    )
    append_audit_log(template_log, role=current_user.role)
    return status.HTTP_200_OK

@router.put("/auto/{device_id}")
def auto(current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN, Role.OPERATOR], isLogged=False))],
            device_id: str, 
            value: bool):
    command = DeviceConfigure(auto=value)
    result = configure_device(device_id, command)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to toggle device")
    client.set_auto(result["mac"], value)
    template_log = AuditLog(
        username=current_user.username,
        action=Action.COMMAND,
        resource="thiết bị",
        detail=f"{"Bật" if value else "Tắt"} chế độ tự động cho thiết bị {result["name"]}"
    )
    append_audit_log(template_log, role=current_user.role)
    return status.HTTP_200_OK

@router.put("/schedule/{device_id}")
def schedule(current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN, Role.OPERATOR], isLogged=False))],
            device_id: str, 
            value: Schedule):
    command = DeviceConfigure(**value.model_dump())
    result = configure_device(device_id, command)
    if not result:
        raise HTTPException(status_code=400, detail="Failed to toggle device")
    client.set_schedule(result["mac"], value)
    template_log = AuditLog(
        username=current_user.username,
        action=Action.COMMAND,
        resource="thiết bị",
        detail=f"Đặt lịch cho thiết bị {result["name"]}"
    )
    append_audit_log(template_log, role=current_user.role)
    return status.HTTP_200_OK

@router.delete("/{device_id}")
def delete(_: Annotated[
    bool, Depends(
    RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN],
                action=Action.DELETE,
                resource="tài khoản"))
    ]
    , device_id: str):
    
    result = delete_device(device_id)
    if result:
        return status.HTTP_200_OK
    raise HTTPException(status_code=400, detail="Failed to delete device")