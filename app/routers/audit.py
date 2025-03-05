# APIs to get audit logs, with filter for username, action, and resource (?username=, ?action=, ?resource=)
# And with time range filter (?start=, ?end=)

from fastapi import APIRouter, Depends
from typing import Annotated
from datetime import datetime

from fastapi.params import Query

from crud.audit import append_audit_log, read_audit_logs
from models.audit import AuditLog
from models.auth import User
from utils.auth import Action, Role, RoleChecker

router = APIRouter(
    prefix="/audit",
    tags=["audit"]
)

@router.get("/", response_model=dict)
def get_filtered_audit_logs(
    user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN]))],
    username: str | None = None,
    action: Action | None = None,
    resource: str | None = None,
    start: datetime | None = Query(None, example="2022-01-01T00:00:00"),
    end: datetime | None = Query(None, example="2022-12-31T23:59:59"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    # Calculate skip based on page and page_size
    skip = (page - 1) * page_size
    
    # Get total count and paginated results
    total_count, results = read_audit_logs(
        username=username,
        action=action,
        resource=resource,
        start=start,
        end=end,
        tenant_id=user.tenant_id,
        skip=skip,
        limit=page_size
    )
    
    # Calculate total pages
    total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1
    
    return {
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "items": results
    }