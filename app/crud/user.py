import bson
from database.mongo import user_collection, tenant_collection
from models.user import AccountEdit, User as Account, AccountCreate
from models.auth import User, Role
import utils.auth as auth
from utils.logging import logger

def create_user(user: AccountCreate) -> Account:
    data = user.model_dump()
    data["hashed_password"] = auth.hash_password(user.password)
    new_user = user_collection.insert_one(data)
    user = Account(
        _id=new_user.inserted_id,
        username=user.username,
        email=user.email,
        role=user.role.value,
        disabled=user.disabled,
    )
    return user

def read_user(user_id: str) -> dict:
    user = user_collection.find_one({"_id": user_id})
    return user

def read_user_by_username(username: str, tenant_id: str | None = None, superAdmin: bool = False) -> User | None:
    if tenant_id:
        user = user_collection.find_one({"username": username, "tenant_id": tenant_id})
    elif superAdmin:
        # Only find superadmin
        user = user_collection.find_one({"username": username, "role": Role.SUPERADMIN.value})
    else:
        user = user_collection.find_one({"username": username})
        
    if user:
        user = User(**user)
        return user
    return None

def read_users(tenant_id: str = "") -> list[Account]:
    if tenant_id != "":
        users = list(user_collection.find({"tenant_id": tenant_id}))
    else:
        users = list(user_collection.find())
        for user in users:
            if "tenant_id" in user:
                tenant = tenant_collection.find_one({"_id": bson.ObjectId(user["tenant_id"])})
                user["tenant"] = tenant
    if not users:
        return []
    return [Account(**user) for user in users]

def update_user(user_id: str, user: AccountEdit):
    try:
        user_data = user.model_dump()
        user_data['role'] = user_data['role'].value
        # Convert _id to ObjectId
        user_id = bson.ObjectId(user_id)
        updated = user_collection.find_one_and_update(
            {"_id": user_id},
            {"$set": user_data},
            upsert=True,
            return_document=True
        )
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        return False
    return updated

def delete_user(user_id: str) -> Account:
    user_id = bson.ObjectId(user_id)
    deleted = user_collection.find_one_and_delete({"_id": user_id})
    return deleted
