from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from routers import api_router
from database import mongo, redis
from database.mongo import user_collection
from utils.auth import hash_password
from utils.config import SUPERADMIN_USERNAME, SUPERADMIN_PASSWORD, SUPERADMIN_EMAIL
from utils.logging import logger

from models.auth import Role
from routers.mqtt import client, Client

def create_superadmin():
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
        mqtt_client: Client = Client()
        mqtt_client.connect()
        mqtt_client.loop_start()
        yield
    finally:
        mongo.client.close()
        mqtt_client.disconnect()

app = FastAPI(
        title="SCADA Traffic Light System",
        description="A SCADA system for controlling traffic lights",
        version="0.1.0",
        lifespan=lifespan
    )

app.include_router(api_router)
    
origins = [
    "http://localhost:3000",
    "http://localhost:5173", # VITE dev server
    "https://scada.chaugiaphat.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)