from typing import Optional

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.services.ingest import fetch_url, store_document, text_from_pdf
from app.services.knowledge import clear_knowledge_cache
from app.services.store import StoreUnavailable, bookings_for, public_key_for, save_tenant, usage_for
from app.services.tenants import clear_tenant_cache

router = APIRouter(prefix="/admin", tags=["admin"])


class TenantCreate(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=120)
    industry: str = Field(default="services", max_length=80)
    agent_name: str = Field(default="Ana", max_length=80)
    greeting_message: str = Field(default="Zdravo, kako mozam da pomognam?", max_length=500)
    system_prompt: str = Field(
        default="Answer only from this tenant's stored facts. Do not invent prices or hours.",
        max_length=4000,
    )


class KnowledgeCreate(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=80)
    source: str = Field(default="notes", max_length=120)
    text: str = Field(default="", max_length=200000)
    url: str = Field(default="", max_length=500)


def _require_admin(
    request: Request,
    settings: Settings = Depends(get_settings),
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> None:
    expected = settings.admin_token.strip()
    if expected:
        if (x_admin_token or "").strip() != expected:
            raise HTTPException(status_code=401, detail="Admin token is required.")
        return
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost", "testclient"):
        raise HTTPException(status_code=403, detail="Admin is only open on this machine.")


def _snippet(settings: Settings, tenant_id: str) -> str:
    base = settings.public_base_url.strip().rstrip("/") or "http://127.0.0.1:8000"
    return (
        '<script src="{base}/sdk.js" data-tenant="{tenant}" data-key="{key}" defer></script>'
    ).format(base=base, tenant=tenant_id, key=public_key_for(tenant_id))


@router.post("/tenants")
def create_tenant(
    payload: TenantCreate,
    _: None = Depends(_require_admin),
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        profile = save_tenant(payload.model_dump())
        clear_tenant_cache()
        tenant_id = profile["id"]
        return {
            "tenant": profile,
            "public_key": profile["public_key"],
            "snippet": _snippet(settings, tenant_id),
            "usage": usage_for(tenant_id),
        }
    except StoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="Tenant store is unavailable.") from exc


@router.post("/knowledge")
def add_knowledge(payload: KnowledgeCreate, _: None = Depends(_require_admin)) -> dict:
    text = payload.text.strip()
    source = payload.source.strip() or "notes"
    if payload.url.strip():
        try:
            text = fetch_url(payload.url.strip())
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        source = payload.url.strip()[:120]
    if not text:
        raise HTTPException(status_code=422, detail="Paste text or a link.")
    try:
        written = store_document(payload.tenant_id, source, text)
    except StoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="Tenant store is unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"tenant_id": payload.tenant_id.strip(), "chunks": written}


@router.post("/knowledge/file")
async def add_knowledge_file(
    tenant_id: str = Form(...),
    upload: UploadFile = File(...),
    _: None = Depends(_require_admin),
) -> dict:
    raw = await upload.read()
    if len(raw) > 5_000_000:
        raise HTTPException(status_code=422, detail="File is larger than 5 MB.")
    name = (upload.filename or "upload").strip()
    if name.lower().endswith(".pdf"):
        try:
            text = text_from_pdf(raw)
        except Exception as exc:
            raise HTTPException(status_code=422, detail="The PDF could not be read.") from exc
    else:
        text = raw.decode("utf-8", errors="replace")
    try:
        written = store_document(tenant_id, name, text)
    except StoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="Tenant store is unavailable.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    clear_knowledge_cache()
    return {"tenant_id": tenant_id.strip(), "chunks": written, "source": name}


@router.get("/snippet/{tenant_id}")
def snippet(
    tenant_id: str,
    _: None = Depends(_require_admin),
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        return {
            "snippet": _snippet(settings, tenant_id),
            "public_key": public_key_for(tenant_id),
            "usage": usage_for(tenant_id),
            "bookings": bookings_for(tenant_id),
        }
    except StoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="Tenant store is unavailable.") from exc
