import re
from html.parser import HTMLParser
from typing import List
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.services.knowledge import clear_knowledge_cache
from app.services.store import delete_knowledge_kind, upsert_knowledge

_CHUNK = 900


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._skip = 0
        self.parts: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style", "noscript"):
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style", "noscript") and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def chunk_text(text: str, size: int = _CHUNK) -> List[str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return []
    pieces = []
    start = 0
    while start < len(cleaned):
        pieces.append(cleaned[start : start + size].strip())
        start += size
    return [piece for piece in pieces if piece]


def text_from_html(raw: str) -> str:
    parser = _TextExtractor()
    parser.feed(raw)
    return " ".join(parser.parts)


def fetch_url(url: str) -> str:
    address = url.strip()
    if not address.startswith("http://") and not address.startswith("https://"):
        raise ValueError("Only http and https links can be imported.")
    request = Request(address, headers={"User-Agent": "b2b-ai-sdk-ingest"})
    try:
        with urlopen(request, timeout=12) as response:
            payload = response.read(500_000)
            charset = response.headers.get_content_charset() or "utf-8"
    except (URLError, TimeoutError, ValueError) as exc:
        raise ValueError("The link could not be read.") from exc
    return text_from_html(payload.decode(charset, errors="replace"))


def text_from_pdf(payload: bytes) -> str:
    from pypdf import PdfReader
    from io import BytesIO

    reader = PdfReader(BytesIO(payload))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def store_document(tenant_id: str, source: str, text: str) -> int:
    """Replace earlier chunks from the same source and store the new pieces."""
    pieces = chunk_text(text)
    if not pieces:
        raise ValueError("There is no text to store.")
    delete_knowledge_kind(tenant_id, "chunk", source)
    rows = []
    for index, piece in enumerate(pieces, start=1):
        rows.append(
            {
                "tenant_id": tenant_id.strip(),
                "kind": "chunk",
                "title": "{source} · {index}".format(source=source[:80], index=index),
                "body": piece,
                "attributes": {"source": source},
            }
        )
    written = upsert_knowledge(rows)
    clear_knowledge_cache()
    return written
