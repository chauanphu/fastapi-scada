from database.mongo import delete_tenant_db, tenant_collection, create_tenant_db
from models.tenant import TenantCreate, Tenant
import bson

def create_tenant(tenant: TenantCreate):
    new_tenant = tenant_collection.insert_one(tenant.model_dump())
    create_tenant_db(str(new_tenant.inserted_id))
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
        {"_id": bson.ObjectId(tenant_id)},
        {"$set": tenant.model_dump(exclude_none=True, exclude_unset=True)},
        return_document=True
    )
    if not tenant:
        return False
    return True

def delete_tenant(tenant_id: str):
    result = tenant_collection.find_one_and_delete({"_id": bson.ObjectId(tenant_id)})
    if not result:
        return False
    delete_tenant_db(tenant_id)
    return True