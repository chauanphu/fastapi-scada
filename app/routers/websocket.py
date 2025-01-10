# Websocket endpoint for real-time monitoring


from typing import List
from fastapi import WebSocket
import asyncio
from models.report import SensorDataResponse
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from crud.report import get_cache_status

router = APIRouter()

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
            data: list[SensorDataResponse] = get_cache_status()
            if not data:
                await asyncio.sleep(5)
                continue
            data = get_cache_status()
            await self.broadcast(data)
            await asyncio.sleep(5)

    # Start a new thread to broadcast data
    def loop(self):
        asyncio.create_task(self.broadcast_data())
        print("Broadcasting task started.")

manager = ConnectionManager()

@router.websocket("/")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        print(f"Error: {e}")
        await manager.disconnect(websocket)