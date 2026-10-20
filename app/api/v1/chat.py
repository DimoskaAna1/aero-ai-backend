import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, Response

from app.config import Settings, get_settings
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat import (
    LLMNotConfiguredError,
    LLMRequestError,
    PromptTooLargeError,
    execute_chat,
)
from app.services.store import StoreUnavailable, consume_message, public_key_for
from app.services.tenants import get_tenant_config

router = APIRouter(prefix="/chat", tags=["chat"])

RATE_LIMIT = 20
RATE_WINDOW_SECONDS = 60
TENANT_HEADER = "X-Tenant-Id"
TENANT_KEY_HEADER = "X-Tenant-Key"


class SlidingWindowLimiter:
    """In-memory limit of requests per key inside a rolling window."""

    def __init__(self, limit: int = RATE_LIMIT, window_seconds: int = RATE_WINDOW_SECONDS) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, keys: List[str]) -> int:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            buckets = [self._events[key] for key in keys]
            for bucket in buckets:
                while bucket and bucket[0] <= cutoff:
                    bucket.popleft()
            blocked = [bucket for bucket in buckets if len(bucket) >= self.limit]
            if blocked:
                oldest = min(bucket[0] for bucket in blocked)
                retry_after = max(1, int(self.window_seconds - (now - oldest)) + 1)
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Try again in {seconds} seconds.".format(
                        seconds=retry_after
                    ),
                    headers={"Retry-After": str(retry_after)},
                )
            for bucket in buckets:
                bucket.append(now)
            return min(self.limit - len(bucket) for bucket in buckets)


limiter = SlidingWindowLimiter()


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _enforce_key(tenant_id: str, tenant_key: Optional[str]) -> None:
    expected = public_key_for(tenant_id)
    if not expected or tenant_key is None or tenant_key.strip() != expected:
        raise HTTPException(status_code=403, detail="X-Tenant-Key does not match this tenant.")


def _enforce_tenant(payload: ChatRequest, tenant_header: Optional[str]) -> str:
    header = (tenant_header or "").strip()
    body = payload.tenant_id.strip()
    if not header:
        raise HTTPException(status_code=400, detail="X-Tenant-Id header is required.")
    if not body or header != body:
        raise HTTPException(
            status_code=403,
            detail="X-Tenant-Id does not match tenant_id.",
        )
    return header


@router.post("", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    x_tenant_id: Optional[str] = Header(default=None, alias=TENANT_HEADER),
    x_tenant_key: Optional[str] = Header(default=None, alias=TENANT_KEY_HEADER),
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    remaining = limiter.hit(
        [
            "ip:{ip}".format(ip=_client_ip(request)),
            "session:{session}".format(session=payload.session_id),
        ]
    )
    response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    header_tenant = _enforce_tenant(payload, x_tenant_id)
    try:
        _enforce_key(header_tenant, x_tenant_key)
        allowance = consume_message(header_tenant)
    except StoreUnavailable as exc:
        raise HTTPException(status_code=503, detail="Tenant store is unavailable.") from exc
    if not allowance["allowed"]:
        raise HTTPException(
            status_code=402,
            detail=(
                "Monthly message limit reached for the {plan} plan ({used}/{limit})."
            ).format(plan=allowance["plan"], used=allowance["used"], limit=allowance["limit"]),
        )
    tenant = get_tenant_config(header_tenant)
    try:
        return execute_chat(
            payload,
            settings,
            background_tasks,
            system_prompt=tenant.system_prompt,
            industry=tenant.industry,
            scoped_tenant_id=header_tenant,
        )
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PromptTooLargeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMRequestError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
