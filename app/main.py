from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from routers import api_router
from database import mongo, redis
from database.mongo import get_users_collection
from utils.auth import hash_password
from utils.config import SUPERADMIN_USERNAME, SUPERADMIN_PASSWORD, SUPERADMIN_EMAIL, FRONTEND_ENDPOINT, DEBUG
from utils.logging import logger
from services.cache_service import cache_service
from services.mqtt import client
from background_tasks import check_idle_devices_task
import asyncio

from models.auth import Role
from services.mqtt import client

def create_superadmin():
    user_collection = get_users_collection()
    if user_collection.count_documents({}) == 0:
        user_collection.insert_one({
            "username": SUPERADMIN_USERNAME,
            "hashed_password": hash_password(SUPERADMIN_PASSWORD),
            "email": SUPERADMIN_EMAIL,
            "role": Role.SUPERADMIN.value,
            "disabled": False,
        })
        logger.info("Created superadmin user")

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        redis.get_redis_connection()
        create_superadmin()
        # Start MQTT client
        client.connect()
        client.loop_start()
        count = cache_service.initialize_device_cache()
        print(f"Initialized cache with {count} devices")
        
        # Start background task for idle device checking
        idle_task = asyncio.create_task(check_idle_devices_task())
        
        yield
        
        # Clean up background task
        idle_task.cancel()
        try:
            await idle_task
        except asyncio.CancelledError:
            pass
            
    finally:
        mongo.client.close()
        client.disconnect()

app = FastAPI(
        title="SCADA Traffic Light System",
        description="A SCADA system for controlling traffic lights",
        version="0.1.0",
        lifespan=lifespan
    )

app.include_router(api_router)
    
origins = [FRONTEND_ENDPOINT]
origins.append("http://localhost:5173")

if DEBUG:
    origins.extend(["http://localhost:3000", "http://localhost:8000", "http://localhost:8080", "http://localhost:80", "http://localhost:5173"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)