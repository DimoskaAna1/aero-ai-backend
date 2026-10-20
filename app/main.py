import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.v1.router import api_router
from app.config import get_settings
from app.database import supabase_configured
from app.schemas.health import HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logger.info(
        "Starting B2B AI SDK API supabase_configured=%s openai_configured=%s",
        supabase_configured(),
        settings.openai_configured,
    )
    if supabase_configured():
        from app.services.store import StoreUnavailable, ensure_demo_tenants, import_legacy_store

        try:
            import_legacy_store()
            ensure_demo_tenants()
        except StoreUnavailable:
            logger.warning("Legacy store import skipped")
    yield


app = FastAPI(
    title="B2B AI SDK",
    version="0.1.0",
    lifespan=lifespan,
)

# Widget embeds are tested from arbitrary customer origins.
# Credentials stay off because browsers reject wildcard origins with credentials.
# Embeds call this API from customer sites. Credentials stay off because
# browsers reject a wildcard origin when credentials are included.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining"],
)

app.include_router(api_router, prefix="/api/v1")

_WIDGET_DIR = Path(__file__).resolve().parents[1] / "widget"
_SDK_FILE = _WIDGET_DIR / "sdk.js"
_ADMIN_FILE = _WIDGET_DIR / "admin.html"


@app.get("/sdk.js", include_in_schema=False)
def embed_sdk() -> FileResponse:
    return FileResponse(
        _SDK_FILE,
        media_type="application/javascript",
        headers={"Cache-Control": "no-cache"},
    )


@app.get("/admin", include_in_schema=False)
def admin_page() -> FileResponse:
    return FileResponse(_ADMIN_FILE, media_type="text/html")


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        supabase_configured=supabase_configured(),
        openai_configured=settings.openai_configured,
    )
