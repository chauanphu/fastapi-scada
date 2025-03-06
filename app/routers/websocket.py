# Websocket endpoint for real-time monitoring
from contextlib import asynccontextmanager
import json
from typing import Optional, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
import asyncio
from models.auth import User
from fastapi import APIRouter
from services.alert import subscribe_alert
from services.cache_service import cache_service
from utils.auth import validate_ws_token
from utils.logging import logger
from redis.client import PubSub
from collections import defaultdict
from crud.audit import append_audit_log, AuditLog

class ConnectionManager:
    def __init__(self):
        self.active_connections: defaultdict[str, dict[str, WebSocket]] = defaultdict(dict)
        self.superAdmin_connections: dict[str, WebSocket] = {}
        self.websocket_info: dict[WebSocket, Tuple[str, str, bool]] = {}  # Maps WebSocket to (tenant_id, user_id, is_super_admin)

    async def connect(self, websocket: WebSocket, tenant_id: str, user_id: str, is_super_admin: bool = False):
        await websocket.accept()
        if is_super_admin:
            self.superAdmin_connections[user_id] = websocket
        else:
            self.active_connections[tenant_id][user_id] = websocket
        self.websocket_info[websocket] = (tenant_id, user_id, is_super_admin)

    async def disconnect(self, websocket: WebSocket, tenant_id: str, user_id: str, is_super_admin: bool = False):
        if is_super_admin:
            self.superAdmin_connections.pop(user_id, None)
            logger.info(f"Connection removed for super-admin: {user_id}")
        else:
            self.active_connections[tenant_id].pop(user_id, None)
            logger.info(f"Connection removed for tenant: {tenant_id}, user: {user_id}")
        if websocket in self.websocket_info:
            del self.websocket_info[websocket]

    async def _remove_disconnected_websocket(self, websocket: WebSocket):
        if websocket in self.websocket_info:
            tenant_id, user_id, is_super_admin = self.websocket_info[websocket]
            await self.disconnect(websocket, tenant_id, user_id, is_super_admin)

    async def broadcast(self, message: str, tenant_id: str):
        connections = list(self.active_connections.get(tenant_id, {}).values())
        super_admins = list(self.superAdmin_connections.values())
        for connection in connections + super_admins:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to connection: {e}")
                await self._remove_disconnected_websocket(connection)

    async def broadcast_data(self):
        while True:
            try:
                if not self.active_connections and not self.superAdmin_connections:
                    await asyncio.sleep(5)
                    continue
                
                # Get devices with states already included in the device data
                devices = cache_service.get_devices_with_states()
                if not devices:
                    await asyncio.sleep(5)
                    continue
                
                # Process device data by tenant
                data_by_tenant = defaultdict(list)
                
                for device_data in devices:
                    tenant_id = device_data.get("tenant_id", "")
                    if tenant_id:
                        # Add the device data directly to the tenant's list
                        data_by_tenant[tenant_id].append(device_data)
                
                # Broadcast data to each tenant
                for tenant_id, tenant_devices in data_by_tenant.items():
                    # Convert the whole list to JSON at once
                    await self.broadcast(json.dumps(tenant_devices), tenant_id)
                
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in broadcast_data loop: {e}")
                await asyncio.sleep(5)

    def loop(self):
        asyncio.create_task(self.broadcast_data())
        logger.info("Broadcasting data started")

manager = ConnectionManager()

class AlertManager(ConnectionManager):
    def __init__(self):
        super().__init__()
        self.pubsub: Optional[PubSub] = None
        self.last_alerts: defaultdict[str, str] = defaultdict(str)
        self.user_alert_status: defaultdict[str, dict[str, str]] = defaultdict(dict)
        self.super_admin_alert_status: dict[str, str] = {}

    async def listen_alert(self, message: str):
        try:
            if message and isinstance(message, dict) and message["type"] == "pmessage":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                json_data = json.loads(data)
                tenant_id = json_data.get("tenant_id")
                if not tenant_id:
                    logger.error("Alert message missing tenant_id")
                    return
                if self.last_alerts[tenant_id] != data:
                    self.last_alerts[tenant_id] = data
                    self.user_alert_status[tenant_id] = {}
                    self.super_admin_alert_status.clear()
                    await self.broadcast(data, tenant_id)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding alert message: {e}")
        except Exception as e:
            logger.error(f"Error processing alert: {e}")

    async def send_last_alert(self, websocket: WebSocket, tenant_id: str, user_id: str, is_super_admin: bool = False):
        try:
            if is_super_admin:
                last_alerts = set(self.last_alerts.values())
                for alert in last_alerts:
                    if self.super_admin_alert_status.get(user_id) != alert:
                        await websocket.send_text(alert)
            else:
                last_alert = self.last_alerts.get(tenant_id)
                if last_alert and self.user_alert_status[tenant_id].get(user_id) != last_alert:
                    await websocket.send_text(last_alert)
        except Exception as e:
            logger.error(f"Error sending last alert: {e}")

    async def acknowledge_alert(self, tenant_id: str, user_id: str, is_super_admin: bool = False):
        try:
            if is_super_admin:
                self.super_admin_alert_status[user_id] = self.last_alerts.get(tenant_id, "")
            else:
                self.user_alert_status[tenant_id][user_id] = self.last_alerts[tenant_id]
            logger.info(f"User {user_id} of tenant {tenant_id} acknowledged the alert.")
        except Exception as e:
            logger.error(f"Error acknowledging alert: {e}")

    async def listen_alert_loop(self):
        while True:
            try:
                if not self.pubsub:
                    self.pubsub = subscribe_alert()
                    self.pubsub.psubscribe("alert:*")
                message = self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
                if message:
                    await self.listen_alert(message)
                await asyncio.sleep(5)
            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Redis connection error: {e}. Reconnecting...")
                self.pubsub = None
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Unexpected error in alert listener loop: {e}")
                await asyncio.sleep(5)

    def loop(self):
        asyncio.create_task(self.listen_alert_loop())
        logger.info("Alert listener started")

    def close(self):
        try:
            if self.pubsub:
                self.pubsub.close()
        except Exception as e:
            logger.error(f"Error closing pubsub: {e}")

alert = AlertManager()

@asynccontextmanager
async def get_manager(_: FastAPI):
    try:
        manager.loop()
        alert.loop()
        yield
    finally:
        manager.active_connections.clear()
        alert.active_connections.clear()
        manager.superAdmin_connections.clear()
        alert.superAdmin_connections.clear()
        alert.close()

router = APIRouter(prefix="/ws", tags=["websocket"], lifespan=get_manager)

async def handle_websocket_auth(websocket: WebSocket) -> Optional[User]:
    try:
        token = websocket.query_params.get("token")
        if not token:
            raise ValueError("Missing token")
        user = await validate_ws_token(token)
        return user
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None

@router.websocket("/monitor/")
async def websocket_monitor(websocket: WebSocket):
    user = await handle_websocket_auth(websocket)
    if not user:
        return

    is_super_admin = user.tenant_id is None
    try:
        await manager.connect(websocket, user.tenant_id, str(user.id), is_super_admin)
        
        while True:
            await websocket.receive_text()  # Maintain connection open
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user.id}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await manager.disconnect(websocket, user.tenant_id, str(user.id), is_super_admin)

@router.websocket("/alert/")
async def websocket_alert(websocket: WebSocket):
    user = await handle_websocket_auth(websocket)
    if not user:
        return

    is_super_admin = user.tenant_id is None
    try:
        await alert.connect(websocket, user.tenant_id, str(user.id), is_super_admin)
        await alert.send_last_alert(websocket, user.tenant_id, str(user.id), is_super_admin)
        while True:
            data = await websocket.receive_text()
            if data == "acknowledge":
                await alert.acknowledge_alert(user.tenant_id, str(user.id), is_super_admin)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user.id}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await alert.disconnect(websocket, user.tenant_id, str(user.id), is_super_admin)