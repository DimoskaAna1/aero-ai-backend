import threading
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from app.services.knowledge import Record


@dataclass
class SessionMemory:
    turns: List[Tuple[str, str]] = field(default_factory=list)
    last_records: List[Record] = field(default_factory=list)
    flow_category: str = ""
    flow_subcategory: str = ""
    flow_product: str = ""


_lock = threading.Lock()
_sessions: Dict[Tuple[str, str], SessionMemory] = {}
_LIMIT = 8


def history(tenant_id: str, session_id: str) -> List[Tuple[str, str]]:
    with _lock:
        session = _sessions.get((tenant_id, session_id))
        if session is None:
            return []
        return list(session.turns)


def last_records(tenant_id: str, session_id: str) -> List[Record]:
    with _lock:
        session = _sessions.get((tenant_id, session_id))
        if session is None:
            return []
        return list(session.last_records)


def remember(
    tenant_id: str,
    session_id: str,
    role: str,
    content: str,
    records: List[Record] = None,
) -> None:
    with _lock:
        session = _sessions.setdefault((tenant_id, session_id), SessionMemory())
        session.turns.append((role, content))
        del session.turns[:-_LIMIT]
        if records is not None:
            session.last_records = list(records)


def flow_position(tenant_id: str, session_id: str) -> Tuple[str, str, str]:
    with _lock:
        session = _sessions.get((tenant_id, session_id))
        if session is None:
            return "", "", ""
        return session.flow_category, session.flow_subcategory, session.flow_product


def set_flow(tenant_id: str, session_id: str, category: str, subcategory: str, product: str) -> None:
    with _lock:
        session = _sessions.setdefault((tenant_id, session_id), SessionMemory())
        session.flow_category = category
        session.flow_subcategory = subcategory
        session.flow_product = product


def clear_memory() -> None:
    with _lock:
        _sessions.clear()
