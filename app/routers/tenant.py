from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

# from crud.user import read_users, create_user, update_user, delete_user
from crud.tenant import read_tenants, create_tenant, update_tenant, delete_tenant
from utils.auth import Role, RoleChecker
from models.tenant import Tenant, TenantCreate
from models.auth import User
from utils.logging import logger

router = APIRouter(
    prefix="/tenant",
    tags=["tenants"]
)

@router.get("/", response_model=list[Tenant])
def get(_: Annotated[
    User, Depends(
    RoleChecker(allowed_roles=[Role.SUPERADMIN]))
    ]):
    return read_tenants()

@router.post("/")
def post(_: Annotated[
    User, Depends(
    RoleChecker(allowed_roles=[Role.SUPERADMIN]))
    ]
    , tenant: TenantCreate):
    try:
        new_tenants = create_tenant(tenant)
        if new_tenants:
            return status.HTTP_201_CREATED
        raise HTTPException(status_code=400, detail="Failed to create tenant")
    except Exception as e:
        logger.error(f"Failed to create tenant: {e}")
        raise HTTPException(status_code=500, detail="Failed to create tenant")

@router.put("/{tenant_id}")
def put(_: Annotated[
    User, Depends(
    RoleChecker(allowed_roles=[Role.SUPERADMIN]))
    ]
    ,
    tenant_id: str,
    tenant: TenantCreate):
    try:
        if not tenant:
            raise HTTPException(status_code=400, detail="No tenant provided")
        success = update_tenant(tenant_id, tenant)
        if success:
            return status.HTTP_200_OK
        raise HTTPException(status_code=400, detail="No tenant updated")
    except Exception as e:
        logger.error(f"Failed to update tenant {tenant_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update tenant")

@router.delete("/{tenant_id}")
def delete(_: Annotated[
    User, Depends(
    RoleChecker(allowed_roles=[Role.SUPERADMIN]))
    ]
    , tenant_id: str):
    try:
        success = delete_tenant(tenant_id)
    except Exception as e:
        logger.error(f"Failed to delete tenant {tenant_id}: {e}")
        raise HTTPException(status_code=400, detail="Failed to delete user")
    if not success:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return status.HTTP_204_NO_CONTENT