from database.mongo import tenant_collection
from database.redis import get_redis_connection
from models.tenant import TenantCreate, Tenant

def create_tenant(tenant: TenantCreate):
    new_tenant = tenant_collection.insert_one(tenant.model_dump())
    return Tenant(
        id=new_tenant.inserted_id,
        name=tenant.name,
        logo=tenant,
        created_date=tenant.created_date,
        disabled=tenant.disabled
    )


def read_tenants():
    tenants = tenant_collection.find()
    return [Tenant(**tenant) for tenant in tenants]

def update_tenant(tenant_id: str, tenant: TenantCreate):
    tenant = tenant_collection.find_one_and_update(
        {"_id": tenant_id},
        {"$set": tenant.model_dump()},
        return_document=True
    )
    return Tenant(**tenant)

def delete_tenant(tenant_id: str):
    tenant_collection.find_one_and_delete({"_id": tenant_id})