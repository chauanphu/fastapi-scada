from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

# from crud.user import read_users, create_user, update_user, delete_user
from crud.user import create_user, read_users, update_user, delete_user
from utils.auth import Role, RoleChecker
from models.audit import Action, AuditLog
from models.user import AccountCreate, AccountEdit, User as Account
from models.auth import User
from utils.logging import logger
from crud.audit import append_audit_log

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.get("/", response_model=list[Account])
def get_users(
    current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN]))]
    ):
    if current_user.role == Role.SUPERADMIN:
        results = read_users()
    else:
        results = read_users(tenant_id=current_user.tenant_id)
        audit = AuditLog(action=Action.READ, username=current_user.username, resource="tài khoản", role=current_user.role.value, detail="Xem danh sách tài khoản")
        append_audit_log(audit, current_user.role, current_user.tenant_id)
    # Exclude superadmin from the list
    if current_user.role != Role.SUPERADMIN:
        results = [user for user in results if user.role != Role.SUPERADMIN]
    return results

@router.post("/", response_model=Account)
def create_new_user(current_user: Annotated[
    User, Depends(
    RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN]))
    ]
    , user: AccountCreate):
    try:
        # Reject if attempt of a non-superadmin to create a superadmin
        if current_user.role != Role.SUPERADMIN and user.role == Role.SUPERADMIN:
            raise HTTPException(status_code=401, detail="Only superadmin can create superadmin")
        # Reject if attempt to create a user with a different tenant_id
        if current_user.role != Role.SUPERADMIN and user.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=401, detail="Cannot create user with different tenant_id")
        new_user = create_user(AccountCreate(**user.model_dump()))
        audit = AuditLog(action=Action.WRITE, username=current_user.username, resource="tài khoản", role=current_user.role.value, detail=f"Tạo tài khoản {new_user.username}")
        append_audit_log(audit, current_user.role, current_user.tenant_id)
        if new_user:
            return new_user
        raise HTTPException(status_code=400, detail="User already exists")
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")

@router.put("/{user_id}")
def put_user(
    current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN]))],
    user_id: str, 
    user: AccountEdit
    ):
    if current_user.role != Role.SUPERADMIN and user.role == Role.SUPERADMIN:
            raise HTTPException(status_code=401, detail="Only superadmin can edit superadmin")
        # Reject if attempt to create a user with a different tenant_id
    if current_user.role != Role.SUPERADMIN and user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=401, detail="Cannot edit user with different tenant_id")
    result = update_user(user_id, user)
    audit = AuditLog(action=Action.UPDATE, username=current_user.username, resource="tài khoản", role=current_user.role.value, detail=f"Cập nhật tài khoản {user.username}")
    append_audit_log(audit, current_user.role, current_user.tenant_id)
    if result:
        return status.HTTP_200_OK
    raise HTTPException(status_code=400, detail="Failed to update user")

@router.delete("/{user_id}")
def delete(
    current_user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN]))]
    , user_id: str):
    # Cannot delete self
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete self")
    result = delete_user(user_id)
    audit = AuditLog(action=Action.DELETE, username=current_user.username, resource="tài khoản", role=current_user.role.value, detail=f"Xóa tài khoản {user_id}")
    append_audit_log(audit, current_user.role, current_user.tenant_id)
    if result:
        return status.HTTP_200_OK
    raise HTTPException(status_code=400, detail="Failed to delete user")