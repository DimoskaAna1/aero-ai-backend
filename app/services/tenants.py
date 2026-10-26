import json
import logging
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

from app.database import get_supabase, supabase_configured
from app.schemas.tenant import QuickChip, TenantConfig
from app.services.flow import opening_choices
from app.services.locale import GREETING_ALL

logger = logging.getLogger(__name__)

_CACHE_SECONDS = 60.0
_cache: Dict[str, Tuple[float, TenantConfig]] = {}
_cache_lock = threading.Lock()

DEFAULT_CHIPS = [
    QuickChip(label="Free Shipping?", message="Is shipping free for this order?"),
    QuickChip(label="Installment Plans", message="What installment plans can I use?"),
    QuickChip(label="10% Discount", message="Can I get 10% off today?"),
]

DEFAULT_SYSTEM_PROMPT = (
    "You are Ana, an e-commerce sales specialist. Help the shopper with products, "
    "shipping, installment plans, and checkout discounts. Stay concise and proactive."
)


def default_tenant_config(tenant_id: str) -> TenantConfig:
    return TenantConfig(
        id=tenant_id,
        name="Demo Store",
        industry="ecommerce",
        agent_name="Ana | Support Specialist",
        greeting_message="Hey, I am Ana. How can I help?",
        quick_chips=list(DEFAULT_CHIPS),
        system_prompt=DEFAULT_SYSTEM_PROMPT,
    )


def clear_tenant_cache() -> None:
    with _cache_lock:
        _cache.clear()


def get_tenant_config(tenant_id: str) -> TenantConfig:
    """Load a tenant row, or the e-commerce fallback when the row is unavailable."""
    key = tenant_id.strip()
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(key)
        if cached is not None and now - cached[0] < _CACHE_SECONDS:
            return _with_menu(cached[1])

    config = _load_tenant_config(key)
    with _cache_lock:
        _cache[key] = (time.monotonic(), config)
    return _with_menu(config)


def _with_menu(config: TenantConfig) -> TenantConfig:
    choices = opening_choices(config.id)
    if not choices:
        return config
    config.quick_chips = [QuickChip(label=choice.label, message=choice.message) for choice in choices]
    config.greeting_message = GREETING_ALL
    return config


def _load_tenant_config(tenant_id: str) -> TenantConfig:
    if not tenant_id or not supabase_configured():
        return default_tenant_config(tenant_id or "demo-tenant")
    try:
        response = (
            get_supabase()
            .table("tenants")
            .select("id,name,industry,agent_name,greeting_message,quick_chips,system_prompt")
            .eq("id", tenant_id)
            .limit(1)
            .execute()
        )
    except Exception as exc:
        logger.warning(
            "Tenant lookup failed tenant=%s error_type=%s",
            tenant_id,
            type(exc).__name__,
        )
        return default_tenant_config(tenant_id)

    rows = getattr(response, "data", None) or []
    if not rows or not isinstance(rows[0], dict):
        return default_tenant_config(tenant_id)
    return _from_row(rows[0], tenant_id)


def _from_row(row: Dict[str, Any], tenant_id: str) -> TenantConfig:
    fallback = default_tenant_config(tenant_id)
    chips = _chips(row.get("quick_chips")) or fallback.quick_chips
    return TenantConfig(
        id=_text(row.get("id"), fallback.id),
        name=_text(row.get("name"), fallback.name),
        industry=_text(row.get("industry"), fallback.industry),
        agent_name=_text(row.get("agent_name"), fallback.agent_name),
        greeting_message=_text(row.get("greeting_message"), fallback.greeting_message),
        quick_chips=chips,
        system_prompt=_text(row.get("system_prompt"), fallback.system_prompt),
    )


def _chips(value: Any) -> List[QuickChip]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return []
    if not isinstance(value, list):
        return []
    chips = []
    for item in value:
        chip = _one_chip(item)
        if chip is not None:
            chips.append(chip)
    return chips


def _one_chip(item: Any) -> Optional[QuickChip]:
    if isinstance(item, str):
        label = item.strip()
        message = label
    elif isinstance(item, dict):
        label = _text(item.get("label") or item.get("text"), "")
        message = _text(item.get("message") or item.get("prompt"), label)
    else:
        return None
    if not label or not message:
        return None
    return QuickChip(label=label[:80], message=message[:500])


def _text(value: Any, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text or fallback
