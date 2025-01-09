from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

# from crud.user import read_users, create_user, update_user, delete_user
from crud.user import create_user, read_users, update_user, delete_user
from utils.auth import Role, RoleChecker
from models.audit import Action
from models.user import AccountCreate, AccountEdit, User as Account
from models.auth import User

router = APIRouter(
    prefix="/users",
    tags=["users"]
)

@router.get("/", response_model=list[Account])
def get_users(current_user: Annotated[
    User, Depends(
    RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN],
                action=Action.READ,
                resource="tài khoản"))
    ]):
    results = read_users()
    # Exclude superadmin from the list
    if current_user.role != Role.SUPERADMIN:
        results = [user for user in results if user.role != Role.SUPERADMIN]
    return results

@router.post("/", response_model=Account)
def create_new_user(_: Annotated[
    User, Depends(
    RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN],
                action=Action.READ,
                resource="tài khoản"))
    ]
    , user: AccountCreate):
    new_user = create_user(user)
    if new_user:
        return new_user
    raise HTTPException(status_code=400, detail="User already exists")

@router.put("/{user_id}")
def put_user(_: Annotated[
    User, Depends(
    RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN],
                action=Action.UPDATE,
                resource="tài khoản"))
    ]
    ,
    user_id: str, 
    user: AccountEdit
    ):
    result = update_user(user_id, user)
    if result:
        return status.HTTP_200_OK
    raise HTTPException(status_code=400, detail="Failed to update user")

@router.delete("/{user_id}")
def delete(current: Annotated[
    User, Depends(
    RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN],
                action=Action.DELETE,
                resource="tài khoản"))
    ]
    , user_id: str):
    # Cannot delete self
    if user_id == current.id:
        raise HTTPException(status_code=400, detail="Cannot delete self")
    
    result = delete_user(user_id)
    if result:
        return status.HTTP_200_OK
    raise HTTPException(status_code=400, detail="Failed to delete user")