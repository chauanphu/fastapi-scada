# Websocket endpoint for real-time monitoring
from contextlib import asynccontextmanager
import json
from typing import List
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
import asyncio
from models.auth import User
from models.report import SensorFull
from fastapi import APIRouter, WebSocket, status
from crud.report import get_cache_status
from services.alert import AlertModel, subscribe_alert
from utils.auth import validate_ws_token
from utils.logging import logger
from redis.client import PubSub

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, List[WebSocket]] = {}
        self.superAdmin_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, tenant_id: str):
        await websocket.accept()
        if not tenant_id:
            self.superAdmin_connections.append(websocket)
        else:
            if tenant_id not in self.active_connections:
                self.active_connections[tenant_id] = []
            self.active_connections[tenant_id].append(websocket)
        print("New connection added")

    async def disconnect(self, websocket: WebSocket, tenant_id: str):
        if not tenant_id:
            self.superAdmin_connections.remove(websocket)
        else:
            self.active_connections[tenant_id].remove(websocket)
        print("Connection removed")

    async def broadcast(self, message: str, tenant_id: str):
        if tenant_id in self.active_connections:
            connections: List[WebSocket] = list(self.active_connections[tenant_id])
        else:
            connections: List[WebSocket] = []
        admin_connections: List[WebSocket] = list(self.superAdmin_connections)
        try:
            for connection in connections:
                await connection.send_text(message)
            for connection in admin_connections:
                await connection.send_text(message)
        except Exception as e:
            print(f"Error: {e}")

    # Broadcast device data to all connected clients every 5 seconds
    async def broadcast_data(self):
        while True:
            # Get all device data from Redis: device:mac as list of objects
            # Skip if empty connectons
            if not self.active_connections and not self.superAdmin_connections:
                await asyncio.sleep(5)
                continue
            data: list[SensorFull] = get_cache_status()
            if not data:
                await asyncio.sleep(5)
                continue
            data_by_tenant = {}
            for d in data:
                if d.tenant_id not in data_by_tenant:
                    data_by_tenant[d.tenant_id] = []
                data_by_tenant[d.tenant_id].append(d.model_dump_json())
            for tenant_id, devices in data_by_tenant.items():
                message = json.dumps(devices)
                await self.broadcast(message, tenant_id)
            await asyncio.sleep(5)

    # Start a new thread to broadcast data
    def loop(self):
        asyncio.create_task(self.broadcast_data())
        logger.info("Broadcasting data started")

manager = ConnectionManager()
class AlertManager(ConnectionManager):
    def __init__(self):
        super().__init__()

    async def listen_alert(self, redis_pubsub: PubSub):
        message = redis_pubsub.get_message()
        if message and message["type"] == "message":
            data = message["data"]
            if isinstance(data, bytes):
                data = data.decode("utf-8")
            data = json.loads(data)
            tenant_id = data["tenant_id"]
            await self.broadcast(json.dumps(data), tenant_id)
        
    async def listen_alert_loop(self, redis_pubsub: PubSub):
        while True:
            await self.listen_alert(redis_pubsub)
            await asyncio.sleep(1)

    def loop(self):
        sub = subscribe_alert()
        asyncio.create_task(self.listen_alert_loop(sub))
        logger.info("Listening to alerts")

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

router = APIRouter(
    prefix="/ws",
    tags=["websocket"],
    lifespan=get_manager
)

@router.get("/monitor/")
async def read_root():
    return status.HTTP_200_OK

@router.get("/notification/")
async def read_notification():
    return status.HTTP_200_OK

@router.websocket("/monitor/")
async def websocket_endpoint(websocket: WebSocket):
    try:
        token = websocket.query_params.get("token")
        user: User = await validate_ws_token(token)
        print(f"User: {user}")
        await manager.connect(websocket, user.tenant_id)
        while True: 
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket, user.tenant_id)
    except Exception as e:
        logger.error(f"Error during websocket /monitor connection: {e}")
        if user and user.tenant_id:
            await manager.disconnect(websocket, user.tenant_id)

@router.websocket("/alert/")
async def websocket_endpoint(websocket: WebSocket):
    try:
        token = websocket.query_params.get("token")
        user: User = await validate_ws_token(token)
        await alert.connect(websocket, user.tenant_id)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await alert.disconnect(websocket, user.tenant_id)
    except Exception as e:
        logger.error(f"Error during websocket /alert connection: {e}")
        if user and user.tenant_id:
            await alert.disconnect(websocket, user.tenant_id)