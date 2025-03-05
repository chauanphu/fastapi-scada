import traceback
from database.mongo import get_alerts_collection
from models.alert import AlertModel, AlertModelFull, AlertSeverity, DeviceState
from utils.logging import logger
from utils import fix_offset

def read_alerts(
    tenant_id: str,
    device: str = None,
    state: DeviceState = None,
    severity: AlertSeverity = None,
    start: str = None,
    end: str = None,
    resolved: bool = None,
    skip: int = 0,
    limit: int = 100
) -> tuple[int, list[AlertModel]]:
    try:
        query = {}
        
        if device:
            query["device"] = device
        if state:
            query["state"] = state
        if severity:
            query["severity"] = severity
        
        # Handle time range filtering
        if start and end:
            query["timestamp"] = {"$gte": start, "$lte": end}
        elif start:
            query["timestamp"] = {"$gte": start}
        elif end:
            query["timestamp"] = {"$lte": end}
        
        # Handle resolved status filtering
        if resolved is not None:
            if resolved:
                query["resolved_time"] = {"$ne": None}
            else:
                query["resolved_time"] = None
        
        # Get the alerts collection
        alerts_collection = get_alerts_collection(tenant_id)
        
        # Get total count for pagination metadata
        total_count = alerts_collection.count_documents(query)
        
        # Get paginated results sorted by timestamp descending (latest first)
        results = alerts_collection.find(query).sort("timestamp", -1).skip(skip).limit(limit)
        
        if results is None:
            return 0, []
        
        # Convert to list and fix timezone offset
        results = [result for result in results]
        for result in results:
            if result.get("timestamp"):
                result["timestamp"] = fix_offset(result["timestamp"])
            if result.get("resolved_time"):
                result["resolved_time"] = fix_offset(result["resolved_time"])
        
        return total_count, [AlertModel(**result) for result in results]
    except Exception as e:
        logger.error(f"Error reading alerts: {e}")
        traceback.print_exc()
        return 0, []
