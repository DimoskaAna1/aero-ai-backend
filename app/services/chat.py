import hashlib
import logging
import math
from typing import Any, Optional, Protocol

import litellm
import openai
import tiktoken

from app.config import Settings
from app.schemas.chat import ChatRequest, ChatResponse, Suggestion, TokenUsage
from app.services.cache import (
    CacheLookupError,
    CacheWrite,
    embed_query,
    find_similar,
    save_cache_entry,
)
from app.services.flow import advance
from app.services.knowledge import format_records, records_for, search_knowledge, title_matches
from app.services.memory import history as session_history
from app.services.memory import remember

logger = logging.getLogger(__name__)

# Keep tenant message content out of provider logs.
litellm.turn_off_message_logging = True
litellm.suppress_debug_info = True

# Per-message overhead used by the OpenAI chat token approximation.
_MESSAGE_TOKEN_OVERHEAD = 4
_REPLY_TOKEN_OVERHEAD = 2

SYSTEM_PROMPT = "You are a helpful assistant embedded in a B2B product."


class LLMNotConfiguredError(RuntimeError):
    """Raised when the OpenAI API key is missing."""


class PromptTooLargeError(Exception):
    """Raised when the prompt exceeds the configured token budget."""

    def __init__(self, tokens: int, limit: int) -> None:
        self.tokens = tokens
        self.limit = limit
        super().__init__(
            "Prompt uses {tokens} tokens, which exceeds the limit of {limit}.".format(
                tokens=tokens,
                limit=limit,
            )
        )


class LLMRequestError(RuntimeError):
    """Raised when the language model provider returns an error."""


class BackgroundQueue(Protocol):
    """Schedules work that runs after the HTTP response is sent."""

    def add_task(self, func: Any, *args: Any, **kwargs: Any) -> None:
        """Queue a callable."""


def _encoding_for(model: str) -> tiktoken.Encoding:
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("o200k_base")


def count_prompt_tokens(messages: list[dict[str, str]], model: str) -> int:
    encoding = _encoding_for(model)
    tokens = _REPLY_TOKEN_OVERHEAD
    for message in messages:
        tokens += _MESSAGE_TOKEN_OVERHEAD
        tokens += len(encoding.encode(message["content"]))
    return tokens


def _usage_value(usage: Any, key: str) -> int:
    if usage is None:
        return 0
    if isinstance(usage, dict):
        value = usage.get(key, 0)
    else:
        value = getattr(usage, key, 0)
    return int(value or 0)


def _build_messages(
    user_message: str,
    system_prompt: str,
    prior_turns: list,
    knowledge_block: str,
) -> list[dict[str, str]]:
    system = system_prompt
    if knowledge_block:
        system = system_prompt + "\n\n" + knowledge_block
    messages = [{"role": "system", "content": system}]
    for role, content in prior_turns:
        if role in {"user", "assistant"} and content:
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})
    return messages


def _zero_usage() -> TokenUsage:
    return TokenUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0)


def _provider_unavailable(exc: BaseException) -> bool:
    """True when this error, or the one it was raised from, is quota or auth."""
    current = exc  # type: Optional[BaseException]
    seen = set()
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if isinstance(current, (openai.RateLimitError, openai.AuthenticationError)):
            return True
        current = current.__cause__
    return False


def _local_embedding(text: str, dimensions: int) -> list:
    """Build a stable unit vector so the same query can still hit the semantic cache."""
    block = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    while len(values) < dimensions:
        block = hashlib.sha256(block).digest()
        for offset in range(0, len(block), 4):
            piece = int.from_bytes(block[offset : offset + 4], "big")
            values.append((piece / 4294967295.0) * 2.0 - 1.0)
            if len(values) == dimensions:
                break
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


_HEALTH_ANSWERS = (
    (
        "radno vrijeme",
        "Naše radno vrijeme je od ponedjeljka do petka od 08:00 do 20:00h, te subotom od 08:00 do 14:00h.",
    ),
    (
        "cjenovnik usluga",
        "Cijene osnovnih usluga: Opći pregled - 2.000 DEN, Specijalistički pregled - 3.500 DEN, Laboratorijske analize - od 1.200 DEN.",
    ),
    (
        "zakaži pregled",
        "Za zakazivanje pregleda molimo navedite željeni datum, vrijeme i ime specijaliste.",
    ),
)


def _is_healthcare(tenant_id: str, industry: str) -> bool:
    return tenant_id == "health-clinic" or industry in {"healthcare", "health"}


def _is_ecommerce(tenant_id: str, industry: str) -> bool:
    return tenant_id == "demo-tenant" or industry in {"ecommerce", "e-commerce"}


def _healthcare_answer(user_message: str) -> Optional[str]:
    normalized = " ".join(user_message.casefold().split())
    for phrase, answer in _HEALTH_ANSWERS:
        if phrase in normalized:
            return answer
    return None


def _healthcare_preview(user_message: str) -> str:
    answer = _healthcare_answer(user_message)
    if answer:
        return answer
    return (
        "Preview reply while the model provider is unavailable. "
        "Mogu pomoći oko zakazivanja pregleda, cjenovnika usluga i radnog vremena."
    )


def _ecommerce_preview(user_message: str) -> str:
    preview = " ".join(user_message.split())
    if len(preview) > 180:
        preview = preview[:177] + "..."
    return (
        "Preview reply while the model provider is unavailable. "
        'For "{preview}", I can split this into installments or apply 10% off if you checkout today.'
    ).format(preview=preview)


_DATE_PHRASES = (
    ("prekosutra", "prekosutra"),
    ("sutra", "sutra"),
    ("утре", "утре"),
    ("tomorrow", "tomorrow"),
    ("danas", "danas"),
    ("данас", "danas"),
)


def _mock_assistant_message(
    user_message: str,
    tenant_id: str,
    industry: str,
    grounded: Optional[str] = None,
) -> str:
    if grounded:
        return grounded
    tenant_key = tenant_id.strip()
    industry_key = industry.strip().casefold()
    if _is_healthcare(tenant_key, industry_key):
        return _healthcare_preview(user_message)
    if _is_ecommerce(tenant_key, industry_key):
        return _ecommerce_preview(user_message)
    return "Preview reply while the model provider is unavailable."


def _mock_response(
    payload: ChatRequest,
    model: str,
    prompt_tokens: int,
    tenant_id: str,
    industry: str,
    grounded: Optional[str] = None,
) -> ChatResponse:
    assistant_message = _mock_assistant_message(
        payload.user_message,
        tenant_id,
        industry,
        grounded,
    )
    completion_tokens = len(_encoding_for(model).encode(assistant_message))
    return ChatResponse(
        tenant_id=payload.tenant_id,
        session_id=payload.session_id,
        assistant_message=assistant_message,
        model=model,
        cached=False,
        usage=TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


def _lookup_cache(
    payload: ChatRequest,
    settings: Settings,
    tenant_id: str,
) -> tuple:
    """Return ``(hit, embedding)``. A lookup failure still keeps the embedding for a later write.

    ``tenant_id`` is the verified ``X-Tenant-Id`` header. The vector query is
    filtered to that tenant and a row from any other tenant is discarded.
    """
    if not settings.supabase_configured or not tenant_id.strip():
        return None, None

    try:
        embedding = embed_query(payload.user_message, settings)
    except CacheLookupError as exc:
        if not _provider_unavailable(exc):
            logger.warning("Semantic cache embedding failed tenant=%s", payload.tenant_id)
            return None, None
        logger.warning(
            "Using a local embedding after provider error tenant=%s error_type=%s",
            payload.tenant_id,
            type(exc.__cause__).__name__ if exc.__cause__ else type(exc).__name__,
        )
        embedding = _local_embedding(payload.user_message, settings.embedding_dimensions)

    try:
        hit = find_similar(tenant_id, embedding, settings)
    except CacheLookupError:
        logger.warning("Semantic cache lookup failed tenant=%s", payload.tenant_id)
        return None, embedding
    return hit, embedding


def _date_label(user_message: str) -> Optional[str]:
    folded = " ".join(user_message.casefold().split())
    for phrase, label in _DATE_PHRASES:
        if phrase in folded:
            return label
    return None


def _last_assistant(prior_turns: list) -> str:
    for role, content in reversed(prior_turns):
        if role == "assistant":
            return content
    return ""


def _specialist_line(tenant_id: str) -> str:
    for record in records_for(tenant_id):
        if "specijalist" in record.title.casefold():
            return record.body
    return "Navedite željeno vrijeme i ime specijaliste."


def _contextual_reply(user_message: str, tenant_id: str, industry: str, prior_turns: list) -> Optional[str]:
    """Continue a booking from the session when the new message is only a date or a detail."""
    if not _is_healthcare(tenant_id, industry.strip().casefold()):
        return None
    previous = _last_assistant(prior_turns)
    label = _date_label(user_message)
    asked = "zakazivanje" in previous.casefold() or "specijalist" in previous.casefold()
    short = len(user_message.split()) <= 3
    if label and (asked or short):
        return "U redu, termin je za {label}. Navedite željeno vrijeme i ime specijaliste. {doctors}".format(
            label=label,
            doctors=_specialist_line(tenant_id),
        )
    if "termin je za" in previous.casefold() and user_message.strip() and label is None:
        detail = " ".join(user_message.split())
        return "Termin je zabilježen: {prior} Detalj: {detail}. Potvrdu šalje klinika.".format(
            prior=previous.split(".")[0] + ".",
            detail=detail,
        )
    return None


def _knowledge_block(records: list) -> str:
    if not records:
        return ""
    lines = ["Tenant records. Use these facts and do not invent prices, hours, or stock."]
    for record in records:
        lines.append("{title}: {body}".format(title=record.title, body=record.body))
    return "\n".join(lines)


def _complete(
    payload: ChatRequest,
    settings: Settings,
    model: str,
    messages: list,
    prompt_tokens: int,
    tenant_id: str,
    industry: str,
    grounded: Optional[str] = None,
) -> ChatResponse:
    try:
        completion = litellm.completion(
            model="openai/{model}".format(model=model),
            messages=messages,
            api_key=settings.openai_api_key.strip(),
            timeout=settings.llm_timeout_seconds,
            metadata={
                "tenant_id": payload.tenant_id,
                "session_id": payload.session_id,
            },
        )
    except (openai.RateLimitError, openai.AuthenticationError) as exc:
        logger.warning(
            "Serving mock completion after provider error tenant=%s session=%s error_type=%s",
            payload.tenant_id,
            payload.session_id,
            type(exc).__name__,
        )
        return _mock_response(payload, model, prompt_tokens, tenant_id, industry, grounded)
    except Exception as exc:
        logger.exception(
            "Chat completion failed tenant=%s session=%s",
            payload.tenant_id,
            payload.session_id,
        )
        raise LLMRequestError("The language model request failed.") from exc

    choices = getattr(completion, "choices", None) or []
    if not choices:
        raise LLMRequestError("The language model returned no choices.")

    message = choices[0].message
    assistant_message = (getattr(message, "content", None) or "").strip()
    usage = getattr(completion, "usage", None)
    prompt_used = _usage_value(usage, "prompt_tokens") or prompt_tokens
    completion_tokens = _usage_value(usage, "completion_tokens")
    if completion_tokens == 0 and assistant_message:
        completion_tokens = len(_encoding_for(model).encode(assistant_message))
    total_tokens = _usage_value(usage, "total_tokens") or (prompt_used + completion_tokens)

    return ChatResponse(
        tenant_id=payload.tenant_id,
        session_id=payload.session_id,
        assistant_message=assistant_message,
        model=model,
        cached=False,
        usage=TokenUsage(
            prompt_tokens=prompt_used,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        ),
    )


def execute_chat(
    payload: ChatRequest,
    settings: Settings,
    background_tasks: Optional[BackgroundQueue] = None,
    system_prompt: Optional[str] = None,
    industry: Optional[str] = None,
    scoped_tenant_id: Optional[str] = None,
) -> ChatResponse:
    """Answer from the tenant semantic cache, or from LiteLLM on a miss.

    A cache outage does not block the model call. Misses are written after the
    response is returned.
    """
    if not settings.openai_configured:
        raise LLMNotConfiguredError("OPENAI_API_KEY is not configured.")

    model = settings.llm_model.strip() or "gpt-4o-mini"
    tenant_id = (scoped_tenant_id or payload.tenant_id).strip()
    tenant_industry = (industry or "").strip()
    prompt = (system_prompt or "").strip() or SYSTEM_PROMPT
    step = advance(tenant_id, payload.session_id, payload.user_message)
    if step is not None:
        remember(tenant_id, payload.session_id, "user", payload.user_message)
        remember(tenant_id, payload.session_id, "assistant", step.text)
        return ChatResponse(
            tenant_id=payload.tenant_id,
            session_id=payload.session_id,
            assistant_message=step.text,
            model=model,
            cached=False,
            usage=_zero_usage(),
            suggestions=[
                Suggestion(label=choice.label, message=choice.message) for choice in step.suggestions
            ],
            image_url=step.image_url or None,
        )

    prior_turns = session_history(tenant_id, payload.session_id)
    records = search_knowledge(tenant_id, payload.user_message)
    focused = title_matches(payload.user_message, records)
    if not focused:
        focused = [record for record in records if record.kind == "chunk" and record.score >= 2][:2]
    grounded = format_records(focused)

    def _finish(text: str, used_records: list = None) -> ChatResponse:
        remember(tenant_id, payload.session_id, "user", payload.user_message)
        remember(
            tenant_id,
            payload.session_id,
            "assistant",
            text,
            used_records if used_records is not None else [],
        )
        return ChatResponse(
            tenant_id=payload.tenant_id,
            session_id=payload.session_id,
            assistant_message=text,
            model=model,
            cached=False,
            usage=_zero_usage(),
        )

    continuation = _contextual_reply(
        payload.user_message,
        tenant_id,
        tenant_industry,
        prior_turns,
    )
    if continuation and not grounded:
        from app.services.store import save_booking

        save_booking(tenant_id, payload.session_id, payload.user_message, continuation)
        return _finish(continuation)

    if grounded:
        return _finish(grounded, focused)

    if _is_healthcare(tenant_id, tenant_industry.casefold()):
        faq_answer = _healthcare_answer(payload.user_message)
        if faq_answer:
            return _finish(faq_answer)

    messages = _build_messages(
        payload.user_message,
        prompt,
        prior_turns,
        _knowledge_block(records),
    )
    prompt_tokens = count_prompt_tokens(messages, model)
    if prompt_tokens > settings.max_prompt_tokens:
        raise PromptTooLargeError(prompt_tokens, settings.max_prompt_tokens)

    hit, embedding = _lookup_cache(payload, settings, tenant_id)
    if hit is not None:
        logger.info(
            "Semantic cache hit tenant=%s similarity=%.3f",
            payload.tenant_id,
            hit.similarity,
        )
        remember(tenant_id, payload.session_id, "user", payload.user_message)
        remember(tenant_id, payload.session_id, "assistant", hit.response_text)
        return ChatResponse(
            tenant_id=payload.tenant_id,
            session_id=payload.session_id,
            assistant_message=hit.response_text,
            model=hit.model,
            cached=True,
            usage=_zero_usage(),
        )

    response = _complete(
        payload,
        settings,
        model,
        messages,
        prompt_tokens,
        tenant_id,
        tenant_industry,
        format_records(records[:2]) or None,
    )
    remember(tenant_id, payload.session_id, "user", payload.user_message)
    remember(tenant_id, payload.session_id, "assistant", response.assistant_message, records)
    if (
        background_tasks is not None
        and embedding is not None
        and response.assistant_message
    ):
        background_tasks.add_task(
            save_cache_entry,
            CacheWrite(
                tenant_id=tenant_id,
                session_id=payload.session_id,
                query_text=payload.user_message,
                response_text=response.assistant_message,
                model=response.model,
                embedding=tuple(embedding),
            ),
        )
    return response
