
from fastapi import APIRouter
from .auth import router as auth_router
from .audit import router as audit_router
from .user import router as user_router

api_router = APIRouter(prefix="/api")
api_router.include_router(auth_router)
api_router.include_router(audit_router)
api_router.include_router(user_router)