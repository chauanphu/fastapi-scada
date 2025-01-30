from datetime import timedelta  
from typing import Annotated  
  
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm  
  
from utils.auth import create_token, authenticate_user
from models.auth import Token  
from utils.config import ACCESS_TOKEN_EXPIRE_MINUTES
from utils.auth import get_current_active_user

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

@router.get("/validate/")
async def validate_token(token: str = Depends(get_current_active_user)):
    return status.HTTP_200_OK
