# APPEND AND READ AUDIT LOGS
from datetime import datetime, timedelta
from database.mongo import audit_collection
from models.audit import AuditLog
from models.auth import Role
from utils.logging import logger

def append_audit_log(audit: AuditLog, role: Role = None) -> None:
    if not role is None:
        if role == Role.SUPERADMIN:
            return
    try:
        new_audit = audit.model_dump()
        new_audit.pop("id", None)
        audit_collection.insert_one(new_audit)
    except Exception as e:
        logger.error(f"Error appending audit log: {e}")

def read_audit_logs(
    username: str = None,
    action: str = None,
    resource: str = None,
    start: str = None,
    end: str = None
) -> list[AuditLog]:
    try:
        query = {}
        if username:
            query["username"] = username
        if action:
            query["action"] = action
        if resource:
            query["resource"] = resource
        if start and end:
            query["timestamp"] = {"$gte": start, "$lte": end}
        elif start:
            query["timestamp"] = {"$gte": start}
        elif end:
            query["timestamp"] = {"$lte": end}
        else:
            # Query for 1 day back
            query["timestamp"] = {"$gte": (datetime.now() - timedelta(days=1)).isoformat()}
            
        # Exclude role == SUPERADMIN
        query["role"] = {"$ne": Role.SUPERADMIN.value}
        return [AuditLog(**audit) for audit in audit_collection.find(query)]
    except Exception as e:
        logger.error(f"Error reading audit logs: {e}")
        return []