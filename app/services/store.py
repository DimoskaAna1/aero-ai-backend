import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEMO_KEYS = {
    "ananas": "pk_ananas_demo",
    "health-clinic": "pk_health_demo",
    "demo-tenant": "pk_demo_tenant",
    "baltic": "pk_baltic_demo",
    "luna": "pk_luna_demo",
}
DEMO_LIMIT = 10000
STARTER_LIMIT = 500
_LEGACY = Path(__file__).resolve().parents[2] / "data" / "store.json"


class StoreUnavailable(RuntimeError):
    """Raised when Supabase cannot read or write tenant state."""


def _client():
    from app.database import get_supabase

    try:
        return get_supabase()
    except Exception as exc:
        raise StoreUnavailable("Supabase is not configured.") from exc


def _rows(response: Any) -> List[Dict[str, Any]]:
    data = getattr(response, "data", None) or []
    if isinstance(data, dict):
        return [data]
    return [row for row in data if isinstance(row, dict)]


def _run(action: str):
    try:
        return action()
    except StoreUnavailable:
        raise
    except Exception as exc:
        logger.warning("Store call failed error_type=%s", type(exc).__name__)
        raise StoreUnavailable("Supabase store call failed.") from exc


def month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


def _new_key() -> str:
    import secrets

    return "pk_" + secrets.token_urlsafe(18)


def _fees(plan: str) -> Dict[str, int]:
    if plan == "demo":
        return {"setup_fee_eur": 0, "monthly_fee_eur": 0}
    return {"setup_fee_eur": 150, "monthly_fee_eur": 39}


def _profile_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    plan = str(row.get("plan") or "starter")
    limit = int(row.get("monthly_message_limit") or STARTER_LIMIT)
    profile = {
        "id": row.get("id"),
        "name": row.get("name"),
        "industry": row.get("industry"),
        "agent_name": row.get("agent_name"),
        "greeting_message": row.get("greeting_message"),
        "quick_chips": row.get("quick_chips") if isinstance(row.get("quick_chips"), list) else [],
        "system_prompt": row.get("system_prompt"),
        "public_key": str(row.get("public_key") or "").strip(),
        "plan": plan,
        "monthly_limit": limit,
        "monthly_message_limit": limit,
    }
    profile.update(_fees(plan))
    return profile


def tenant_profile(tenant_id: str) -> Optional[Dict[str, Any]]:
    key = tenant_id.strip()
    if not key:
        return None

    def read():
        return (
            _client()
            .table("tenants")
            .select(
                "id,name,industry,agent_name,greeting_message,quick_chips,system_prompt,"
                "public_key,plan,monthly_message_limit"
            )
            .eq("id", key)
            .limit(1)
            .execute()
        )

    rows = _rows(_run(read))
    matched = [row for row in rows if str(row.get("id") or "") == key]
    if not matched:
        return None
    return _profile_from_row(matched[0])


def public_key_for(tenant_id: str) -> str:
    key = tenant_id.strip()
    profile = tenant_profile(key)
    if profile and profile.get("public_key"):
        return str(profile["public_key"])
    if key in DEMO_KEYS:
        return _store_demo_key(key, profile is not None)
    return ""


def _store_demo_key(tenant_id: str, row_exists: bool) -> str:
    demo_key = DEMO_KEYS[tenant_id]
    if row_exists:
        def update():
            return (
                _client()
                .table("tenants")
                .update({"public_key": demo_key, "plan": "demo", "monthly_message_limit": DEMO_LIMIT})
                .eq("id", tenant_id)
                .execute()
            )

        _run(update)
        return demo_key
    return ""


def ensure_demo_tenants() -> None:
    """Keep the built-in demos addressable when their row or key is missing."""
    if tenant_profile("luna") is None:
        save_tenant(
            {
                "id": "luna",
                "name": "LUNA",
                "industry": "ecommerce",
                "agent_name": "Ana | LUNA",
                "greeting_message": "Zdravo. Izberi jezik.",
                "quick_chips": [],
                "system_prompt": "Answer only from the LUNA fashion catalog. Do not invent prices.",
                "public_key": DEMO_KEYS["luna"],
                "plan": "demo",
                "monthly_message_limit": DEMO_LIMIT,
            }
        )
    if tenant_profile("baltic") is None:
        save_tenant(
            {
                "id": "baltic",
                "name": "Baltic View",
                "industry": "hotel",
                "agent_name": "Ana | Stay",
                "greeting_message": "Zdravo. Izberi jezik.",
                "quick_chips": [],
                "system_prompt": "Answer only from this hotel's rooms and extras. Do not invent rates.",
                "public_key": DEMO_KEYS["baltic"],
                "plan": "demo",
                "monthly_message_limit": DEMO_LIMIT,
            }
        )
    if tenant_profile("health-clinic") is None:
        save_tenant(
            {
                "id": "health-clinic",
                "name": "Health Clinic",
                "industry": "healthcare",
                "agent_name": "Ana | Care Coordinator",
                "greeting_message": "Zdravo, kako mozam da pomognam?",
                "quick_chips": [],
                "system_prompt": "Answer only from this clinic's stored facts. Do not diagnose or invent prices.",
                "public_key": DEMO_KEYS["health-clinic"],
                "plan": "demo",
                "monthly_message_limit": DEMO_LIMIT,
            }
        )
    for tenant_id in DEMO_KEYS:
        public_key_for(tenant_id)
    try:
        seeded = seed_tenant_catalog("luna")
        if seeded:
            logger.info("Seeded LUNA catalog rows=%s", seeded)
    except Exception as exc:
        logger.warning("LUNA catalog seed skipped error_type=%s", type(exc).__name__)


def save_tenant(profile: Dict[str, Any]) -> Dict[str, Any]:
    tenant_id = str(profile.get("id") or "").strip()
    if not tenant_id:
        raise ValueError("Tenant id is required.")
    current = tenant_profile(tenant_id) or {}
    current.update({key: value for key, value in profile.items() if value is not None})
    current["id"] = tenant_id
    if not str(current.get("public_key") or "").strip():
        current["public_key"] = DEMO_KEYS.get(tenant_id) or _new_key()
    if tenant_id in DEMO_KEYS:
        current["plan"] = current.get("plan") or "demo"
        current["monthly_message_limit"] = int(current.get("monthly_message_limit") or current.get("monthly_limit") or DEMO_LIMIT)
    else:
        current["plan"] = current.get("plan") or "starter"
        current["monthly_message_limit"] = int(
            current.get("monthly_message_limit") or current.get("monthly_limit") or STARTER_LIMIT
        )
    row = {
        "id": tenant_id,
        "name": str(current.get("name") or tenant_id),
        "industry": str(current.get("industry") or "services"),
        "agent_name": str(current.get("agent_name") or "Ana"),
        "greeting_message": str(current.get("greeting_message") or "Zdravo, kako mozam da pomognam?"),
        "quick_chips": current.get("quick_chips") if isinstance(current.get("quick_chips"), list) else [],
        "system_prompt": str(
            current.get("system_prompt")
            or "Answer only from this tenant's stored facts. Do not invent prices or hours."
        ),
        "public_key": str(current["public_key"]),
        "plan": str(current["plan"]),
        "monthly_message_limit": int(current["monthly_message_limit"]),
    }

    def write():
        return _client().table("tenants").upsert(row, on_conflict="id").execute()

    _run(write)
    saved = tenant_profile(tenant_id)
    return saved or _profile_from_row(row)


def _limits(tenant_id: str, profile: Dict[str, Any]) -> Dict[str, Any]:
    if tenant_id in DEMO_KEYS and not profile:
        plan = "demo"
        limit = DEMO_LIMIT
    else:
        plan = str(profile.get("plan") or "starter")
        limit = int(profile.get("monthly_message_limit") or profile.get("monthly_limit") or STARTER_LIMIT)
    return {"plan": plan, "limit": limit}


def consume_message(tenant_id: str) -> Dict[str, Any]:
    """Count one chat message for this tenant and month."""
    key = tenant_id.strip()
    profile = tenant_profile(key) or {}
    bounds = _limits(key, profile)
    month = month_key()
    rpc_result = _consume_with_rpc(key, month)
    if rpc_result is not None:
        return rpc_result
    return _consume_with_table(key, month, bounds)


def _consume_with_rpc(tenant_id: str, month: str) -> Optional[Dict[str, Any]]:
    try:
        response = _client().rpc(
            "consume_tenant_message",
            {"p_tenant": tenant_id, "p_month": month},
        ).execute()
    except Exception as exc:
        logger.info("Usage counter uses the table error_type=%s", type(exc).__name__)
        return None
    payload = getattr(response, "data", None)
    if isinstance(payload, list):
        payload = payload[0] if payload else None
    if isinstance(payload, dict) and "allowed" in payload:
        return {
            "allowed": bool(payload.get("allowed")),
            "used": int(payload.get("used") or 0),
            "limit": int(payload.get("limit") or STARTER_LIMIT),
            "plan": str(payload.get("plan") or "starter"),
        }
    return None


def _consume_with_table(tenant_id: str, month: str, bounds: Dict[str, Any]) -> Dict[str, Any]:
    limit = int(bounds["limit"])
    plan = str(bounds["plan"])

    def read():
        return (
            _client()
            .table("tenant_usage")
            .select("tenant_id,month,message_count")
            .eq("tenant_id", tenant_id)
            .eq("month", month)
            .limit(1)
            .execute()
        )

    rows = [
        row
        for row in _rows(_run(read))
        if str(row.get("tenant_id") or "") == tenant_id and str(row.get("month") or "") == month
    ]
    used = int(rows[0].get("message_count") or 0) if rows else 0
    if used >= limit:
        return {"allowed": False, "used": used, "limit": limit, "plan": plan}
    used += 1

    def write():
        return (
            _client()
            .table("tenant_usage")
            .upsert(
                {"tenant_id": tenant_id, "month": month, "message_count": used},
                on_conflict="tenant_id,month",
            )
            .execute()
        )

    _run(write)
    return {"allowed": True, "used": used, "limit": limit, "plan": plan}


def usage_for(tenant_id: str) -> Dict[str, Any]:
    key = tenant_id.strip()
    profile = tenant_profile(key) or {}
    bounds = _limits(key, profile)
    month = month_key()

    def read():
        return (
            _client()
            .table("tenant_usage")
            .select("tenant_id,month,message_count")
            .eq("tenant_id", key)
            .eq("month", month)
            .limit(1)
            .execute()
        )

    rows = [
        row
        for row in _rows(_run(read))
        if str(row.get("tenant_id") or "") == key and str(row.get("month") or "") == month
    ]
    used = int(rows[0].get("message_count") or 0) if rows else 0
    result = {
        "tenant_id": key,
        "month": month,
        "used": used,
        "limit": bounds["limit"],
        "plan": bounds["plan"],
    }
    result.update(_fees(str(bounds["plan"])))
    return result


def save_booking(tenant_id: str, session_id: str, when_text: str, detail: str) -> Dict[str, Any]:
    row = {
        "tenant_id": tenant_id.strip(),
        "session_id": session_id.strip(),
        "when_text": " ".join(when_text.split()),
        "detail": " ".join(detail.split()),
    }

    def write():
        return _client().table("tenant_bookings").insert(row).execute()

    saved = _rows(_run(write))
    return saved[0] if saved else row


def bookings_for(tenant_id: str) -> List[Dict[str, Any]]:
    key = tenant_id.strip()

    def read():
        return (
            _client()
            .table("tenant_bookings")
            .select("tenant_id,session_id,when_text,detail,created_at")
            .eq("tenant_id", key)
            .order("created_at")
            .limit(200)
            .execute()
        )

    return [row for row in _rows(_run(read)) if str(row.get("tenant_id") or "") == key]


def knowledge_for(tenant_id: str) -> List[Dict[str, Any]]:
    key = tenant_id.strip()
    if not key:
        return []

    rows = []
    start = 0
    while start < 5000:

        def read(start=start):
            return (
                _client()
                .table("tenant_knowledge")
                .select("tenant_id,kind,title,body,attributes")
                .eq("tenant_id", key)
                .range(start, start + 499)
                .execute()
            )

        chunk = _rows(_run(read))
        if not chunk:
            break
        for row in chunk:
            if str(row.get("tenant_id") or "") != key:
                continue
            title = str(row.get("title") or "").strip()
            body = str(row.get("body") or "").strip()
            if not title or not body:
                continue
            attributes = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
            rows.append(
                {
                    "tenant_id": key,
                    "kind": str(row.get("kind") or "fact"),
                    "title": title,
                    "body": body,
                    "attributes": attributes,
                }
            )
        if len(chunk) < 500:
            break
        start += 500
    return rows


def upsert_knowledge(rows: List[Dict[str, Any]]) -> int:
    payload = []
    for row in rows:
        tenant_id = str(row.get("tenant_id") or "").strip()
        title = str(row.get("title") or "").strip()
        body = str(row.get("body") or "").strip()
        if not tenant_id or not title or not body:
            continue
        payload.append(
            {
                "tenant_id": tenant_id,
                "kind": str(row.get("kind") or "fact"),
                "title": title,
                "body": body,
                "attributes": row.get("attributes") if isinstance(row.get("attributes"), dict) else {},
            }
        )
    if not payload:
        return 0

    saved = 0
    for start in range(0, len(payload), 200):
        batch = payload[start : start + 200]

        def write(batch=batch):
            return (
                _client()
                .table("tenant_knowledge")
                .upsert(batch, on_conflict="tenant_id,title")
                .execute()
            )

        _run(write)
        saved += len(batch)
    return saved


def seed_tenant_catalog(tenant_id: str) -> int:
    """Upsert the in-memory catalog into tenant_knowledge when the table is behind."""
    from app.services.flow import knowledge_rows

    key = tenant_id.strip()
    rows = []
    for row in knowledge_rows(key):
        rows.append(
            {
                "tenant_id": key,
                "kind": row["kind"],
                "title": row["title"],
                "body": row["body"],
                "attributes": row["attributes"],
            }
        )
    if not rows or _knowledge_count(key) >= len(rows):
        return 0
    return upsert_knowledge(rows)


def _knowledge_count(tenant_id: str) -> int:
    def read():
        return (
            _client()
            .table("tenant_knowledge")
            .select("id", count="exact")
            .eq("tenant_id", tenant_id)
            .limit(1)
            .execute()
        )

    response = _run(read)
    return int(getattr(response, "count", None) or 0)


def delete_knowledge_kind(tenant_id: str, kind: str, source: str) -> None:
    key = tenant_id.strip()

    def read():
        return (
            _client()
            .table("tenant_knowledge")
            .select("tenant_id,title,kind,attributes")
            .eq("tenant_id", key)
            .eq("kind", kind)
            .limit(500)
            .execute()
        )

    titles = []
    for row in _rows(_run(read)):
        if str(row.get("tenant_id") or "") != key or str(row.get("kind") or "") != kind:
            continue
        attributes = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
        if attributes.get("source") == source and row.get("title"):
            titles.append(row["title"])
    if not titles:
        return

    def remove():
        return (
            _client()
            .table("tenant_knowledge")
            .delete()
            .eq("tenant_id", key)
            .in_("title", titles)
            .execute()
        )

    _run(remove)


def import_legacy_store() -> int:
    """Copy data/store.json into Supabase once, then rename the file so it is not read again."""
    if not _LEGACY.exists():
        return 0
    try:
        loaded = json.loads(_LEGACY.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        logger.warning("Legacy store file could not be read")
        return 0
    if not isinstance(loaded, dict):
        return 0
    tenants = loaded.get("tenants") if isinstance(loaded.get("tenants"), dict) else {}
    imported = 0
    for profile in tenants.values():
        if isinstance(profile, dict) and profile.get("id"):
            limit = profile.get("monthly_limit")
            if limit is not None and "monthly_message_limit" not in profile:
                profile = dict(profile)
                profile["monthly_message_limit"] = limit
            save_tenant(profile)
            imported += 1
    knowledge = loaded.get("knowledge") if isinstance(loaded.get("knowledge"), list) else []
    upsert_knowledge([row for row in knowledge if isinstance(row, dict)])
    usage = loaded.get("usage") if isinstance(loaded.get("usage"), dict) else {}
    for bucket, count in usage.items():
        tenant_id, separator, month = str(bucket).partition(":")
        if not separator or not tenant_id or not month:
            continue
        _client().table("tenant_usage").upsert(
            {"tenant_id": tenant_id, "month": month, "message_count": int(count or 0)},
            on_conflict="tenant_id,month",
        ).execute()
    bookings = loaded.get("bookings") if isinstance(loaded.get("bookings"), list) else []
    for booking in bookings:
        if not isinstance(booking, dict):
            continue
        tenant_id = str(booking.get("tenant_id") or "").strip()
        session_id = str(booking.get("session_id") or "")
        when_text = str(booking.get("when_text") or "")
        already = any(
            row.get("session_id") == session_id and row.get("when_text") == " ".join(when_text.split())
            for row in bookings_for(tenant_id)
        )
        if already:
            continue
        save_booking(tenant_id, session_id, when_text, str(booking.get("detail") or ""))
    renamed = _LEGACY.with_name("store.json.imported")
    _LEGACY.replace(renamed)
    logger.info("Imported legacy store tenants=%s", imported)
    return imported
