# Websocket endpoint for real-time monitoring
from contextlib import asynccontextmanager
import json
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from models.audit import Action
from models.auth import User
from fastapi import APIRouter
from crud.report import get_cache_status
from services.alert import subscribe_alert
from utils.auth import validate_ws_token
from utils.logging import logger
from redis.client import PubSub
from collections import defaultdict
from crud.audit import append_audit_log, AuditLog

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: defaultdict[str, dict[str, WebSocket]] = defaultdict(dict)
        self.superAdmin_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, tenant_id: str, user_id: str, is_super_admin: bool = False):
        await websocket.accept()
        if is_super_admin:
            self.superAdmin_connections[user_id] = websocket
            print(f"Connection added for super-admin: {user_id}")
        else:
            self.active_connections[tenant_id][user_id] = websocket
            print(f"Connection added for tenant: {tenant_id}, user: {user_id}")

    async def disconnect(self, websocket: WebSocket, tenant_id: str, user_id: str, is_super_admin: bool = False):
        if is_super_admin:
            self.superAdmin_connections.pop(user_id, None)
            print(f"Connection removed for super-admin: {user_id}")
        else:
            self.active_connections[tenant_id].pop(user_id, None)
            print(f"Connection removed for tenant: {tenant_id}, user: {user_id}")

    async def broadcast(self, message: str, tenant_id: str):
        # Send to tenant-specific users
        connections = self.active_connections.get(tenant_id, {}).values()
        # Send to super-admins
        super_admins = self.superAdmin_connections.values()
        try:
            for connection in connections:
                await connection.send_text(message)
            for connection in super_admins:
                await connection.send_text(message)
        except Exception as e:
            logger.error(f"Error during broadcast to tenant {tenant_id}: {e}")

    async def broadcast_data(self):
        while True:
            if not self.active_connections and not self.superAdmin_connections:
                await asyncio.sleep(5)
                continue
            data = get_cache_status()
            if not data:
                await asyncio.sleep(5)
                continue
            data_by_tenant = defaultdict(list)
            for d in data:
                data_by_tenant[d.tenant_id].append(d.model_dump_json())
            for tenant_id, devices in data_by_tenant.items():
                await self.broadcast(json.dumps(devices), tenant_id)
            await asyncio.sleep(5)

    def loop(self):
        asyncio.create_task(self.broadcast_data())
        logger.info("Broadcasting data started")

manager = ConnectionManager()

class AlertManager(ConnectionManager):
    def __init__(self):
        super().__init__()
        self.pubsub: PubSub = None
        self.last_alerts: defaultdict[str, str] = defaultdict(str)
        self.user_alert_status: defaultdict[str, dict[str, str]] = defaultdict(dict)  # Tracks user acknowledgment
        self.super_admin_alert_status: dict[str, str] = {}  # Tracks super-admin acknowledgment

    async def listen_alert(self, message: str):
        try:
            if message and isinstance(message, dict) and message["type"] == "pmessage":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                json_data = json.loads(data)
                tenant_id = json_data.get("tenant_id")
                if self.last_alerts[tenant_id] != data:
                    self.last_alerts[tenant_id] = data
                    self.user_alert_status[tenant_id] = {}  # Reset user acknowledgment
                    self.super_admin_alert_status.clear()  # Reset super-admin acknowledgment
                    await self.broadcast(data, tenant_id)
        except json.JSONDecodeError:
            logger.error(f"Error decoding alert message: {message}")
        except Exception as e:
            logger.error(f"Error processing alert: {e}")

    async def send_last_alert(self, websocket: WebSocket, tenant_id: str, user_id: str, is_super_admin: bool = False):
        if is_super_admin:
            last_alerts = set(self.last_alerts.values())
            for alert in last_alerts:
                if self.super_admin_alert_status.get(user_id) != alert:
                    await websocket.send_text(alert)
        else:
            last_alert = self.last_alerts.get(tenant_id)
            if last_alert and self.user_alert_status[tenant_id].get(user_id) != last_alert:
                await websocket.send_text(last_alert)

    async def acknowledge_alert(self, tenant_id: str, user_id: str, is_super_admin: bool = False):
        if is_super_admin:
            self.super_admin_alert_status[user_id] = self.last_alerts.get(tenant_id, "")
        else:
            self.user_alert_status[tenant_id][user_id] = self.last_alerts[tenant_id]
        logger.info(f"User {user_id} of tenant {tenant_id} acknowledged the alert.")

    async def listen_alert_loop(self):
        self.pubsub = subscribe_alert()
        self.pubsub.psubscribe("alert:*")
        while True:
            message = self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
            if message:
                await self.listen_alert(message)
            await asyncio.sleep(5)

    def loop(self):
        asyncio.create_task(self.listen_alert_loop())
        logger.info("Alert listener started")

    def close(self):
        if self.pubsub:
            self.pubsub.close()

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

@router.websocket("/monitor/")
async def websocket_monitor(websocket: WebSocket):
    try:
        token = websocket.query_params.get("token")
        user: User = await validate_ws_token(token)
        is_super_admin = user.tenant_id is None
        await manager.connect(websocket, user.tenant_id, str(user.id), is_super_admin)
        await alert.send_last_alert(websocket, user.tenant_id, str(user.id), is_super_admin)
        signin_log = AuditLog(action=Action.LOGIN, username=user.username, resource="hệ thống", role=user.role, detail="Đăng nhập")
        logout_log = AuditLog(action=Action.LOGOUT, username=user.username, resource="hệ thống", role=user.role, detail="Đăng xuất")
        append_audit_log(signin_log, role=user.role, tenant_id=user.tenant_id)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user.tenant_id, str(user.id), is_super_admin)
        if user:
            append_audit_log(logout_log, role=user.role, tenant_id=user.tenant_id)
    except Exception as e:
        logger.error(f"Error during /monitor connection: {e}")
        await manager.disconnect(websocket, user.tenant_id, str(user.id), is_super_admin)
        if user:
            append_audit_log(logout_log, role=user.role, tenant_id=user.tenant_id)

@router.websocket("/alert/")
async def websocket_alert(websocket: WebSocket):
    try:
        token = websocket.query_params.get("token")
        user: User = await validate_ws_token(token)
        is_super_admin = user.tenant_id is None
        await alert.connect(websocket, user.tenant_id, str(user.id), is_super_admin)
        await alert.send_last_alert(websocket, user.tenant_id, str(user.id), is_super_admin)
        while True:
            data = await websocket.receive_text()
            if data == "acknowledge":
                await alert.acknowledge_alert(user.tenant_id, str(user.id), is_super_admin)
    except WebSocketDisconnect:
        await alert.disconnect(websocket, user.tenant_id, str(user.id), is_super_admin)
    except Exception as e:
        logger.error(f"Error during /alert connection: {e}")
        await alert.disconnect(websocket, user.tenant_id, str(user.id), is_super_admin)