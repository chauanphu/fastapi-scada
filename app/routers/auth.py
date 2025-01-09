from datetime import datetime, timedelta  
from typing import Annotated  
  
from fastapi import APIRouter, Depends, HTTPException  
from fastapi.security import OAuth2PasswordRequestForm  
  
from crud.audit import append_audit_log
from models.audit import AuditLog
from utils.auth import Action, Role, RoleChecker, create_token, authenticate_user, validate_refresh_token
# from data import fake_users_db, refresh_tokens  
from models.auth import User, Token  
from database.redis import set_refresh_token, remove_refresh_token

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
) 
  
ACCESS_TOKEN_EXPIRE_MINUTES = 20 # 20 minutes  
REFRESH_TOKEN_EXPIRE_MINUTES = 120   # 2 hours
  
@router.get("/data")  
def get_data(_: Annotated[bool, Depends(
    RoleChecker(allowed_roles=[Role.ADMIN, Role.SUPERADMIN],
                action=Action.READ,
                resource="data"))
    ]):   
  return {"data": "This is important data"}   
  
@router.post("/token")  
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:  
        raise HTTPException(status_code=400, detail="Incorrect username or password")  
      
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES)  
    append_audit_log(
        AuditLog(username=user.username, action=Action.LOGIN.value, resource="token", timestamp=datetime.now(), role=user.role.value),
        role=user.role
    )
    access_token = create_token(data={"sub": user.username, "role": user.role.value}, expires_delta=access_token_expires)  
    refresh_token = create_token(data={"sub": user.username, "role": user.role.value}, expires_delta=refresh_token_expires)  
    set_refresh_token(refresh_token,refresh_token_expires)
    return Token(access_token=access_token, refresh_token=refresh_token)  
  
@router.post("/refresh")  
async def refresh_access_token(token_data: Annotated[tuple[User, str], Depends(validate_refresh_token)]):  
    user, token = token_data 
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  
    refresh_token_expires = timedelta(minutes=REFRESH_TOKEN_EXPIRE_MINUTES) 
    access_token = create_token(data={"sub": user.username, "role": user.role.value}, expires_delta=access_token_expires)  
    refresh_token = create_token(data={"sub": user.username, "role": user.role.value}, expires_delta=refresh_token_expires)  
  
    remove_refresh_token(token)
    set_refresh_token(refresh_token, refresh_token_expires)
    return Token(access_token=access_token, refresh_token=refresh_token)
