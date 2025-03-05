# APPEND AND READ AUDIT LOGS
from database.mongo import get_audit_collection
from models.audit import AuditLog
from models.auth import Role
from utils.logging import logger
from utils import fix_offset

def append_audit_log(audit: AuditLog, role: Role = None, tenant_id: str = None):
    if not role is None:
        if role == Role.SUPERADMIN:
            return
    try:
        new_audit = audit.model_dump()
        new_audit.pop("id", None)
        audit_collection = get_audit_collection(tenant_id)
        audit_collection.insert_one(new_audit)
    except Exception as e:
        logger.error(f"Error appending audit log: {e}")

def read_audit_logs(
    tenant_id: str,
    username: str = None,
    action: str = None,
    resource: str = None,
    start: str = None,
    end: str = None,
    skip: int = 0,
    limit: int = 100
) -> tuple[int, list[AuditLog]]:
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
            
        audit_collection = get_audit_collection(tenant_id)
        
        # Get total count for pagination metadata
        total_count = audit_collection.count_documents(query)
        
        # Get paginated results sorted by timestamp descending (latest first)
        results = audit_collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        
        if results is None:
            return 0, []
        
        # The results is in UTC+0, convert and offset to local timezone
        results = [result for result in results]
        for result in results:
            result["timestamp"] = fix_offset(result["timestamp"])
        
        return total_count, [AuditLog(**result) for result in results]
    except Exception as e:
        logger.error(f"Error reading audit logs: {e}")
        return 0, []