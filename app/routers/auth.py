from datetime import timedelta  
from typing import Annotated  
  
from fastapi import APIRouter, Depends, HTTPException  
from fastapi.security import OAuth2PasswordRequestForm  
  
from utils.auth import create_token, authenticate_user
from models.auth import Token  
from utils.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(
    prefix="/auth",
    tags=["auth"]
) 
  
@router.post("/token")  
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:  
        raise HTTPException(status_code=400, detail="Incorrect username or password")  
      
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  
    access_token = create_token(
        data={
            "sub": user.username, 
            "role": user.role.value,
            "tenant_id": user.tenant_id
            }, expires_delta=access_token_expires)  
    return Token(access_token=access_token, tenant_id=user.tenant_id, role=user.role)
