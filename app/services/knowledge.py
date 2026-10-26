import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_TOKEN = re.compile(r"[0-9A-Za-z\u00C0-\u024F]+")
_FOLDS = str.maketrans(
    {
        "š": "s",
        "č": "c",
        "ć": "c",
        "ž": "z",
        "đ": "d",
    }
)
_lock = threading.Lock()
_cache: Dict[str, List["Record"]] = {}
_seeded = set()


@dataclass(frozen=True)
class Record:
    tenant_id: str
    kind: str
    title: str
    body: str
    attributes: Dict[str, Any] = field(default_factory=dict)
    score: int = 0


def _fold(text: str) -> str:
    from app.services.flow import _fold as fold_text

    return fold_text(text.translate(_FOLDS))


def _tokens(text: str) -> List[str]:
    return [token for token in _TOKEN.findall(_fold(text)) if len(token) > 2]


def search_knowledge(tenant_id: str, query: str) -> List[Record]:
    """Return tenant records whose title or body shares words with the question."""
    wanted = set(_tokens(query))
    if not wanted:
        return []
    ranked = []
    scoped = tenant_id.strip()
    for record in records_for(scoped):
        if record.tenant_id != scoped:
            continue
        title = set(_tokens(record.title))
        body = set(_tokens(record.body))
        score = (2 * len(wanted & title)) + len(wanted & body)
        if score <= 0:
            continue
        ranked.append(
            Record(
                tenant_id=record.tenant_id,
                kind=record.kind,
                title=record.title,
                body=record.body,
                attributes=record.attributes,
                score=score,
            )
        )
    ranked.sort(key=lambda record: record.score, reverse=True)
    return ranked[:3]


def records_for(tenant_id: str) -> List[Record]:
    key = tenant_id.strip()
    with _lock:
        cached = _cache.get(key)
        if cached is not None:
            return cached
    _seed(key)
    by_title: Dict[str, Record] = {}
    for record in BUNDLED:
        if record.tenant_id == key:
            by_title[record.title] = record
    from app.services.flow import knowledge_rows

    for row in knowledge_rows(key):
        by_title[row["title"]] = _row_record(key, row)
    for record in _from_supabase(key):
        if record.tenant_id != key:
            continue
        by_title[record.title] = record
    loaded = [record for record in by_title.values() if record.title]
    with _lock:
        _cache[key] = loaded
    return loaded


def _row_record(tenant_id: str, row: dict) -> Record:
    attributes = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
    return Record(
        tenant_id=tenant_id,
        kind=str(row.get("kind") or "fact"),
        title=str(row.get("title") or "").strip(),
        body=str(row.get("body") or "").strip(),
        attributes=attributes,
    )


def _seed(tenant_id: str) -> None:
    """Write the bundled facts and the catalog into tenant_knowledge once."""
    if tenant_id in _seeded:
        return
    from app.services.flow import knowledge_rows
    from app.services.store import upsert_knowledge

    rows = []
    for record in BUNDLED:
        if record.tenant_id != tenant_id:
            continue
        rows.append(
            {
                "tenant_id": tenant_id,
                "kind": record.kind,
                "title": record.title,
                "body": record.body,
                "attributes": record.attributes,
            }
        )
    for row in knowledge_rows(tenant_id):
        rows.append(
            {
                "tenant_id": tenant_id,
                "kind": row["kind"],
                "title": row["title"],
                "body": row["body"],
                "attributes": row["attributes"],
            }
        )
    if not rows:
        _seeded.add(tenant_id)
        return
    try:
        upsert_knowledge(rows)
    except Exception as exc:
        logger.warning(
            "Knowledge seed skipped tenant=%s error_type=%s",
            tenant_id,
            type(exc).__name__,
        )
        return
    _seeded.add(tenant_id)


def clear_knowledge_cache() -> None:
    with _lock:
        _cache.clear()


def _from_supabase(tenant_id: str) -> List[Record]:
    try:
        from app.database import get_supabase, supabase_configured

        if not supabase_configured():
            return []
        rows = []
        start = 0
        while start < 5000:
            response = (
                get_supabase()
                .table("tenant_knowledge")
                .select("tenant_id,kind,title,body,attributes")
                .eq("tenant_id", tenant_id)
                .range(start, start + 499)
                .execute()
            )
            chunk = getattr(response, "data", None) or []
            rows.extend(row for row in chunk if isinstance(row, dict))
            if len(chunk) < 500:
                break
            start += 500
    except Exception as exc:
        logger.warning(
            "Knowledge lookup failed tenant=%s error_type=%s",
            tenant_id,
            type(exc).__name__,
        )
        return []
    records = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = str(row.get("title") or "").strip()
        body = str(row.get("body") or "").strip()
        if not title or not body:
            continue
        attributes = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
        row_tenant = str(row.get("tenant_id") or "").strip()
        if row_tenant != tenant_id:
            continue
        records.append(
            Record(
                tenant_id=row_tenant,
                kind=str(row.get("kind") or "fact"),
                title=title,
                body=body,
                attributes=attributes,
            )
        )
    return records


def title_matches(query: str, records: List[Record]) -> List[Record]:
    """Keep the records whose titles actually contain the question words."""
    wanted = set(_tokens(query))
    if not wanted:
        return []
    ranked = []
    for record in records:
        overlap = len(wanted & set(_tokens(record.title)))
        if overlap:
            ranked.append((overlap, record.score, record))
    if not ranked:
        return []
    ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best = ranked[0][0]
    return [record for overlap, _score, record in ranked if overlap == best][:2]


def format_records(records: List[Record]) -> str:
    if not records:
        return ""
    if len(records) == 1:
        return records[0].body
    return "\n\n".join(record.body for record in records)


BUNDLED = [
    Record(
        tenant_id="health-clinic",
        kind="faq",
        title="Radno vrijeme",
        body=(
            "Naše radno vrijeme je od ponedjeljka do petka od 08:00 do 20:00h, "
            "te subotom od 08:00 do 14:00h."
        ),
    ),
    Record(
        tenant_id="health-clinic",
        kind="faq",
        title="Cjenovnik usluga",
        body=(
            "Cijene osnovnih usluga: Opći pregled - 2.000 DEN, "
            "Specijalistički pregled - 3.500 DEN, Laboratorijske analize - od 1.200 DEN."
        ),
    ),
    Record(
        tenant_id="health-clinic",
        kind="faq",
        title="Zakaži pregled",
        body="Za zakazivanje pregleda molimo navedite željeni datum, vrijeme i ime specijaliste.",
    ),
    Record(
        tenant_id="health-clinic",
        kind="service",
        title="Specijalisti",
        body="Dostupni specijalisti: Dr. Ana Petrov (opći pregled), Dr. Marko Iliev (specijalistički pregled).",
        attributes={"doctors": ["Dr. Ana Petrov", "Dr. Marko Iliev"]},
    ),
    Record(
        tenant_id="ananas",
        kind="policy",
        title="Dostava",
        body=(
            "Besplatna dostava za porudžbine preko 3.000 MKD. "
            "Ispod tog iznosa dostava je 150 MKD. Isporuka stiže za 1 do 3 radna dana."
        ),
        attributes={"free_over_mkd": 3000, "fee_mkd": 150},
    ),
    Record(
        tenant_id="ananas",
        kind="policy",
        title="Plaćanje na rate",
        body=(
            "Plaćanje na 6 ili 12 rata bez kamate važi za proizvode skuplje od 6.000 MKD. "
            "Iznos rate piše uz svaki proizvod u katalogu."
        ),
    ),
    Record(
        tenant_id="ananas",
        kind="product",
        title="Samsung Galaxy A55 8/128",
        body=(
            "Samsung Galaxy A55 8/128, telefoni. Cena 24.990 MKD. "
            "Na 12 rata po 2.083 MKD. Besplatna dostava."
        ),
        attributes={"category": "Telefoni", "brand": "Samsung", "price_mkd": 24990, "installments": 12, "installment_mkd": 2083},
    ),
    Record(
        tenant_id="ananas",
        kind="product",
        title="iPhone 13 128GB",
        body="iPhone 13 128GB, telefoni. Cena 42.990 MKD. Na 12 rata po 3.583 MKD. Besplatna dostava.",
        attributes={"category": "Telefoni", "brand": "Apple", "price_mkd": 42990, "installments": 12, "installment_mkd": 3583},
    ),
    Record(
        tenant_id="ananas",
        kind="product",
        title="Beko veš mašina 8 kg",
        body=(
            "Beko veš mašina 8 kg, 1200 obrtaja, bela tehnika. Cena 27.990 MKD. "
            "Na 12 rata po 2.333 MKD. Besplatna dostava."
        ),
        attributes={"category": "Bela tehnika", "brand": "Beko", "price_mkd": 27990, "installments": 12, "installment_mkd": 2333},
    ),
    Record(
        tenant_id="ananas",
        kind="product",
        title="Gorenje frižider NRK 619",
        body="Gorenje kombinovani frižider NRK 619, bela tehnika. Cena 32.490 MKD. Na 12 rata po 2.708 MKD.",
        attributes={"category": "Bela tehnika", "brand": "Gorenje", "price_mkd": 32490, "installments": 12, "installment_mkd": 2708},
    ),
    Record(
        tenant_id="ananas",
        kind="product",
        title="Lenovo IdeaPad 3",
        body="Lenovo IdeaPad 3, laptop 15.6 inča, 16 GB RAM. Cena 36.990 MKD. Na 12 rata po 3.083 MKD.",
        attributes={"category": "Laptopovi", "brand": "Lenovo", "price_mkd": 36990, "installments": 12, "installment_mkd": 3083},
    ),
    Record(
        tenant_id="ananas",
        kind="product",
        title="Xiaomi robot usisivač",
        body="Xiaomi robot usisivač, mali kućni aparati. Cena 18.490 MKD. Na 6 rata po 3.082 MKD.",
        attributes={"category": "Mali kućni aparati", "brand": "Xiaomi", "price_mkd": 18490, "installments": 6, "installment_mkd": 3082},
    ),
    Record(
        tenant_id="ananas",
        kind="product",
        title="Philips sušilo za kosu",
        body="Philips sušilo za kosu, lična nega. Cena 4.290 MKD. Jednokratno plaćanje, rate nisu dostupne ispod 6.000 MKD.",
        attributes={"category": "Lična nega", "brand": "Philips", "price_mkd": 4290, "installments": 0},
    ),
    Record(
        tenant_id="ananas",
        kind="product",
        title="Nike Revolution 7",
        body="Nike Revolution 7, patike za trčanje. Cena 5.990 MKD. Jednokratno plaćanje.",
        attributes={"category": "Sport", "brand": "Nike", "price_mkd": 5990, "installments": 0},
    ),
]
