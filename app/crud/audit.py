# APPEND AND READ AUDIT LOGS
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

def read_audit_logs() -> list[AuditLog]:
    try:
        logs = list(audit_collection.find())
        logs = [AuditLog(**log) for log in logs]
        return logs
    except Exception as e:
        logger.error(f"Error reading audit logs: {e}")
        return []