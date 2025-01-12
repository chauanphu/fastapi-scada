# Websocket endpoint for real-time monitoring


from contextlib import asynccontextmanager
import threading
from typing import List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from models.report import SensorFull, SensorModel
from fastapi import APIRouter, WebSocket
from crud.report import get_cache_status
from utils.auth import validate_ws_token
from utils.logging import logger
from database.redis import subscribe

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self.lock:
            self.active_connections.append(websocket)
        print("New connection added")

    async def disconnect(self, websocket: WebSocket):
        async with self.lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        print("Connection removed")

    async def broadcast(self, message: str):
        async with self.lock:
            connections = list(self.active_connections)
        try:
            for connection in connections:
                await connection.send_text(message)
        except Exception as e:
            print(f"Error: {e}")

    # Broadcast device data to all connected clients every 5 seconds
    async def broadcast_data(self):
        while True:
            # Get all device data from Redis: device:mac as list of objects
            async with self.lock:
                connections = list(self.active_connections)
            if not connections:
                await asyncio.sleep(5)
                continue
            data: list[SensorFull] = get_cache_status()
            if not data:
                await asyncio.sleep(5)
                continue
            data: list[SensorFull] = get_cache_status()
            # Convert data to JSON string
            data = [d.model_dump_json() for d in data]
            await self.broadcast(data)
            await asyncio.sleep(5)

    # Start a new thread to broadcast data
    def loop(self):
        asyncio.create_task(self.broadcast_data())
        logger.info("Broadcasting data started")

manager = ConnectionManager()
notification = ConnectionManager()

@asynccontextmanager
async def get_manager(_: FastAPI):
    try:
        manager.loop()
        # Subscribe to the "notification" channel
        asyncio.create_task(subscribe("alert", notification.broadcast))
        logger.info("Started Redis subscription to 'alert' channel")
        yield
    finally:
        print("Manager closed.")

router = APIRouter(
    prefix="/ws",
    tags=["websocket"],
    lifespan=get_manager
)

@router.get("/")
async def read_root():
    return {"message": "Hello World"}

@router.websocket("/monitor/")
async def websocket_endpoint(websocket: WebSocket):
    try:
        token = websocket.query_params.get("token")
        user = await validate_ws_token(token)
        await manager.connect(websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"Error: {e}")
        await manager.disconnect(websocket)

@router.websocket("/noti/")
async def websocket_endpoint(websocket: WebSocket):
    try:
        token = websocket.query_params.get("token")
        user = await validate_ws_token(token)
        await notification.connect(websocket)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await notification.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error: {e}")
        await notification.disconnect(websocket)