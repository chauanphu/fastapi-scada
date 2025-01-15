from typing import Annotated, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from models.auth import Role
from models.report import EnergyReportResponse
from crud.report import agg_daily, agg_hourly, agg_monthly
from utils.auth import RoleChecker

router = APIRouter(
    prefix="/report",
    tags=["report"]
)

@router.get("/", response_model=list[EnergyReportResponse])
async def get_energy_report(
    current_user: Annotated[bool, Depends(RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN, Role.MONITOR]))],
    device_id: str,
    start_date: Optional[datetime] = Query(None, example="2023-07-01T00:00:00Z"),
    end_date: Optional[datetime] = Query(None, example="2023-12-31T23:59:59Z"),
    aggregation: Optional[str] = Query(
        "hourly",
        regex="^(monthly|daily|hourly)$",
        description="Aggregation level: monthly, daily, or hourly",
    ),
):
    """
    Flexible endpoint to query energy consumption report with time range and aggregation level.
    """
    if aggregation == "monthly":
        results = agg_monthly(current_user, device_id, start_date, end_date)
    elif aggregation == "daily":
        results = agg_daily(current_user, device_id, start_date, end_date)
    elif aggregation == "hourly":
        results = agg_hourly(current_user, device_id, start_date, end_date)
    else:
        raise HTTPException(status_code=400, detail="Invalid aggregation level")

    return results