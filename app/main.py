from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from routers import api_router
from database import mongo

app = FastAPI(
        title="SCADA Traffic Light System",
        description="A SCADA system for controlling traffic lights",
        version="0.1.0",
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