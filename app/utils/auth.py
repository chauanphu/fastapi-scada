#auth.py  
from enum import Enum
from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer   
from passlib.context import CryptContext  
from jose import JWTError, jwt  
from datetime import datetime, timedelta, timezone  
from fastapi import Depends, HTTPException, status
from pydantic import ValidationError

from .config import ALGORITHM, SECRET_KEY
from models.auth import Action, Role, User  
from database.redis import check_refresh_token
from crud.user import read_user_by_username

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/token")  
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  

def authenticate_user(username: str, password: str) -> User | bool:  
    user = read_user_by_username(username)
    if not user:  
        return False  
    if not pwd_context.verify(password, user.hashed_password):
        return False  
    return user

def hash_password(password: str):
    return pwd_context.hash(password)

async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):  
    credentials_exception = HTTPException(  
        status_code=status.HTTP_401_UNAUTHORIZED,  
        detail="Could not validate credentials",  
        headers={"WWW-Authenticate": "Bearer"},  
    )  
    try:  
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  
        username: str = payload.get("sub")  
        if username is None:  
            raise credentials_exception  
    except JWTError:  
        raise credentials_exception  
    user = read_user_by_username(username)
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
  def __init__(self, allowed_roles: list[Role], action: Action):
    self.allowed_roles = allowed_roles  
    self.action = action

  def _audit_log(self, user: User, action: Action):
    raise NotImplementedError

  def __call__(self, user: Annotated[User, Depends(get_current_active_user)]):
    if user.role in self.allowed_roles:
      return True  
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="You don't have enough permissions"
        )  
  
async def validate_refresh_token(token: Annotated[str, Depends(oauth2_scheme)]):  
    credentials_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")  
    try:  
        if not check_refresh_token(token):
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])  
            username: str = payload.get("sub")  
            role: str = payload.get("role")  
            if username is None or role is None:  
                raise credentials_exception  
        else:  
            raise credentials_exception  
  
    except (JWTError, ValidationError):  
        raise credentials_exception  
  
    user = read_user_by_username(username)
  
    if user is None:  
        raise credentials_exception  
  
    return user, token  