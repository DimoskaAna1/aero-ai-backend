from fastapi import APIRouter

from app.schemas.tenant import TenantConfig
from app.services.tenants import get_tenant_config

router = APIRouter(prefix="/tenant-config", tags=["tenants"])


@router.get("/{tenant_id}", response_model=TenantConfig)
def tenant_config(tenant_id: str) -> TenantConfig:
    return get_tenant_config(tenant_id.strip())
