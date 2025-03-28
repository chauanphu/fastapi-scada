#auth.py  
from typing import Annotated
from fastapi import Depends, HTTPException, Header
from fastapi.security import OAuth2PasswordBearer   
from passlib.hash import bcrypt
from jose import JWTError, jwt  
from datetime import datetime, timedelta, timezone  
from fastapi import Depends, HTTPException, status
from pydantic import ValidationError

from .config import ALGORITHM, SECRET_KEY
from models.auth import Role, User  
from models.audit import Action
from crud.user import read_user_by_username

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")  

def authenticate_user(username: str, password: str) -> User | bool:  
    user = read_user_by_username(username)
    if not user:  
        return False
    if not bcrypt.verify(password, user.hashed_password):
        return False  
    return user

def hash_password(password: str):
    return bcrypt.hash(password)

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):  
    credentials_exception = HTTPException(  
        status_code=status.HTTP_401_UNAUTHORIZED,  
        detail="Could not validate credentials",  
        headers={"WWW-Authenticate": "Bearer"},  
    )  
    try:  
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  
        username: str = payload.get("sub")  
        tenant_id: str = payload.get("tenant_id")
        if username is None:
            raise credentials_exception
    except JWTError:  
        raise credentials_exception  
    user = read_user_by_username(username, tenant_id, superAdmin=True)
    if user is None:  
        raise credentials_exception  
    return user  
  
async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]):  
    if current_user.disabled:  
        raise HTTPException(status_code=400, detail="Inactive user")  
    return current_user 

def create_token(data: dict, expires_delta: timedelta | None = None):  
    to_encode = data.copy()  
    if expires_delta:  
        expire = datetime.now(timezone.utc) + expires_delta  
    else:  
        expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode.update({"exp": expire})  
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)  
    return encoded_jwt

class RoleChecker:  
  def __init__(self, allowed_roles: list[Role] | str):
    self.allowed_roles = allowed_roles  

  def __call__(self, user: Annotated[User, Depends(get_current_active_user)]):
    if self.allowed_roles == "*":
        return user
    elif user.role in self.allowed_roles:
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="You don't have enough permissions"
        )  

# Token validation for websocket connections
async def validate_ws_token(token: str):
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")  
    try:
        if token is None:
            raise credentials_exception
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise credentials_exception
    except (JWTError, ValidationError):  
        raise credentials_exception  
  
    user = read_user_by_username(username)
  
    if user is None:  
        raise credentials_exception  
  
    return user