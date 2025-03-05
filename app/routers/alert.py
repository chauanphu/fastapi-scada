from fastapi import APIRouter, Depends, Query
from typing import Annotated, Optional
from datetime import datetime

from crud.alert import read_alerts
from models.alert import AlertModel, AlertSeverity, DeviceState
from models.auth import User
from utils.auth import Role, RoleChecker

router = APIRouter(
    prefix="/alert",
    tags=["alert"]
)

@router.get("/", response_model=dict)
def get_filtered_alerts(
    user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN, Role.MONITOR]))],
    device: Optional[str] = None,
    state: Optional[DeviceState] = None,
    severity: Optional[AlertSeverity] = None,
    start: Optional[datetime] = Query(None, example="2022-01-01T00:00:00"),
    end: Optional[datetime] = Query(None, example="2022-12-31T23:59:59"),
    resolved: Optional[bool] = None,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    # Calculate skip based on page and page_size
    skip = (page - 1) * page_size
    
    # Get total count and paginated results
    total_count, results = read_alerts(
        tenant_id=user.tenant_id,
        device=device,
        state=state,
        severity=severity,
        start=start,
        end=end,
        resolved=resolved,
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
