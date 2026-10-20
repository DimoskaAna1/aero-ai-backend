from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Sequence

from openai import OpenAI
from postgrest.types import ReturnMethod

from app.config import Settings
from app.database import DatabaseNotConfiguredError, get_supabase

logger = logging.getLogger(__name__)

_MATCH_FUNCTION = "match_semantic_cache"
_CACHE_TABLE = "semantic_cache"


class CacheLookupError(RuntimeError):
    """Raised when embedding or the vector lookup cannot be completed."""


@dataclass(frozen=True)
class CacheHit:
    response_text: str
    model: str
    similarity: float


@dataclass(frozen=True)
class CacheWrite:
    tenant_id: str
    session_id: str
    query_text: str
    response_text: str
    model: str
    embedding: tuple


def to_vector_literal(values: Sequence[float]) -> str:
    """Format an embedding as a pgvector literal. Values are numeric only."""
    if not values:
        raise CacheLookupError("Embedding was empty.")
    parts = []
    for value in values:
        number = float(value)
        if not math.isfinite(number):
            raise CacheLookupError("Embedding contained a non-finite value.")
        parts.append(repr(number))
    return "[" + ",".join(parts) + "]"


def embed_query(text: str, settings: Settings) -> list:
    """Embed one user query with the OpenAI embeddings API."""
    if not settings.openai_configured:
        raise CacheLookupError("OPENAI_API_KEY is not configured.")

    model = settings.embedding_model.strip() or "text-embedding-3-small"
    try:
        client = OpenAI(
            api_key=settings.openai_api_key.strip(),
            timeout=settings.llm_timeout_seconds,
        )
        response = client.embeddings.create(
            model=model,
            input=text,
            dimensions=settings.embedding_dimensions,
        )
    except Exception as exc:
        raise CacheLookupError("Embedding request failed.") from exc

    rows = getattr(response, "data", None) or []
    if not rows:
        raise CacheLookupError("Embedding response was empty.")

    raw = getattr(rows[0], "embedding", None) or []
    embedding = [float(value) for value in raw]
    if len(embedding) != settings.embedding_dimensions:
        raise CacheLookupError("Embedding dimensions did not match the cache schema.")
    return embedding


def find_similar(
    tenant_id: str,
    embedding: Sequence[float],
    settings: Settings,
) -> CacheHit | None:
    """Return the nearest tenant-scoped cache row above the similarity threshold."""
    scoped_tenant = tenant_id.strip()
    if not settings.supabase_configured or not scoped_tenant:
        return None

    threshold = settings.cache_similarity_threshold
    try:
        client = get_supabase()
        response = client.rpc(
            _MATCH_FUNCTION,
            {
                "query_embedding": to_vector_literal(embedding),
                "match_tenant_id": scoped_tenant,
                "match_threshold": threshold,
                "match_count": 1,
            },
        ).execute()
    except DatabaseNotConfiguredError:
        return None
    except CacheLookupError:
        raise
    except Exception as exc:
        raise CacheLookupError("Semantic cache lookup failed.") from exc

    rows = [
        row
        for row in _rows(getattr(response, "data", None))
        if str(row.get("tenant_id") or "") == scoped_tenant
    ]
    if not rows:
        returned = _rows(getattr(response, "data", None))
        if returned:
            logger.warning(
                "Discarded semantic cache row outside tenant scope tenant=%s",
                scoped_tenant,
            )
        return None

    row = rows[0]

    try:
        similarity = float(row.get("similarity"))
    except (TypeError, ValueError):
        return None
    # Spec is strictly above the threshold. 0.85 itself is a miss.
    if similarity <= threshold:
        return None

    response_text = str(row.get("response_text") or "").strip()
    if not response_text:
        return None

    model = str(row.get("model") or "").strip() or settings.llm_model
    return CacheHit(
        response_text=response_text,
        model=model,
        similarity=similarity,
    )


def save_cache_entry(entry: CacheWrite) -> None:
    """Insert one cache row. Failures are logged and never raised to the caller."""
    try:
        client = get_supabase()
        client.table(_CACHE_TABLE).insert(
            {
                "tenant_id": entry.tenant_id,
                "session_id": entry.session_id,
                "query_text": entry.query_text,
                "response_text": entry.response_text,
                "model": entry.model,
                "embedding": to_vector_literal(entry.embedding),
            },
            returning=ReturnMethod.minimal,
        ).execute()
    except Exception as exc:
        logger.warning(
            "Semantic cache write failed tenant=%s error_type=%s",
            entry.tenant_id,
            type(exc).__name__,
        )


def _rows(data: Any) -> list:
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []
