# Websocket endpoint for real-time monitoring
from contextlib import asynccontextmanager
import json
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from models.auth import User
from fastapi import APIRouter
from crud.report import get_cache_status
from services.alert import subscribe_alert
from utils.auth import validate_ws_token
from utils.logging import logger
from redis.client import PubSub
from collections import defaultdict

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: defaultdict[str, List[WebSocket]] = defaultdict(list)
        self.superAdmin_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, tenant_id: str):
        await websocket.accept()
        if not tenant_id:
            self.superAdmin_connections.append(websocket)
        else:
            self.active_connections[tenant_id].append(websocket)
        logger.info("New connection added")

    async def disconnect(self, websocket: WebSocket, tenant_id: str):
        if not tenant_id:
            self.superAdmin_connections.remove(websocket)
        else:
            self.active_connections[tenant_id].remove(websocket)
        logger.info("Connection removed")

    async def broadcast(self, message: str, tenant_id: str):
        connections = self.active_connections.get(tenant_id, [])
        try:
            for connection in connections + self.superAdmin_connections:
                await connection.send_text(message)
        except Exception as e:
            logger.error(f"Error during broadcast: {e}")

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

    async def listen_alert(self, message: str):
        try:
            if message and isinstance(message, dict) and message["type"] == "pmessage":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                json_data = json.loads(data)
                tenant_id = json_data.get("tenant_id")
                await self.broadcast(data, tenant_id)
        except json.JSONDecodeError:
            logger.error(f"Error decoding alert message: {message}")
        except Exception as e:
            logger.error(f"Error processing alert: {e}")

    async def listen_alert_loop(self):
        self.pubsub = subscribe_alert()
        self.pubsub.psubscribe("alert:*")
        while True:
            if self.active_connections or self.superAdmin_connections:
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
async def get_manager(app: FastAPI):
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
        await manager.connect(websocket, user.tenant_id)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user.tenant_id)
    except Exception as e:
        logger.error(f"Error during /monitor connection: {e}")
        await manager.disconnect(websocket, user.tenant_id)

@router.websocket("/alert/")
async def websocket_alert(websocket: WebSocket):
    try:
        token = websocket.query_params.get("token")
        user: User = await validate_ws_token(token)
        await alert.connect(websocket, user.tenant_id)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await alert.disconnect(websocket, user.tenant_id)
    except Exception as e:
        logger.error(f"Error during /alert connection: {e}")
        await alert.disconnect(websocket, user.tenant_id)