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
from utils import local_tz, get_real_time

router = APIRouter(
    prefix="/audit",
    tags=["audit"]
)

@router.get("/", response_model=list[AuditLog])
def get_filtered_audit_logs(
    user: Annotated[User, Depends(RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN]))],
    username: str | None = None,
    action: Action | None = None,
    resource: str | None = None,
    start: datetime | None = Query(None, example="2022-01-01T00:00:00"),
    end: datetime | None = Query(None, example="2022-12-31T23:59:59")
):
    results = read_audit_logs(username=username, action=action, resource=resource, start=start, end=end, tenant_id=user.tenant_id)
    audit = AuditLog(action=Action.READ, username=user.username, resource="nhật ký", role=user.role.value, detail="Xem nhật ký hoạt động")
    append_audit_log(audit, user.role, user.tenant_id)
    return results