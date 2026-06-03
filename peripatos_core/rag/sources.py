"""Source ingester for RAG pipeline."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from bs4 import BeautifulSoup

from peripatos_core.exceptions import IngestError
from peripatos_core.http import request_with_retry
from peripatos_core.fetcher import PaperFetcher
from peripatos_core.parser import PDFParser

SourceKind = Literal["pdf", "html", "markdown", "text", "arxiv"]

_ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")


@dataclass
class Source:
    """Ingested source ready for chunking and embedding."""

    kind: SourceKind
    raw_bytes: bytes
    content_text: str
    content_hash: str
    origin: str


def _hash(kind: str, raw_bytes: bytes) -> str:
    return hashlib.sha256(kind.encode() + b":" + raw_bytes).hexdigest()


def _strip_html(html_bytes: bytes) -> str:
    soup = BeautifulSoup(html_bytes, "html.parser")
    for tag in soup(["script", "style", "nav", "footer"]):
        tag.decompose()
    return soup.get_text(separator="\n\n")


def _is_arxiv(source_input: str) -> bool:
    if _ARXIV_ID_RE.match(source_input):
        return True
    return "arxiv.org" in source_input


def _load_arxiv_or_pdf(source_input: str, kind: SourceKind, mineru_token: str | None = None) -> Source:
    fetcher = PaperFetcher()
    parser = PDFParser(mineru_token=mineru_token)
    pdf_path, _ = fetcher.fetch(source_input)
    raw_bytes = Path(pdf_path).read_bytes()
    parsed = parser.parse(Path(pdf_path))
    text = parsed.markdown or parsed.full_text
    return Source(
        kind=kind,
        raw_bytes=raw_bytes,
        content_text=text,
        content_hash=_hash(kind, raw_bytes),
        origin=source_input,
    )


def _load_html(source_input: str) -> Source:
    resp = request_with_retry("GET", source_input, timeout=60)
    resp.raise_for_status()
    raw_bytes = resp.content
    text = _strip_html(raw_bytes)
    return Source(
        kind="html",
        raw_bytes=raw_bytes,
        content_text=text,
        content_hash=_hash("html", raw_bytes),
        origin=source_input,
    )


def _load_local_file(path: Path, kind: SourceKind) -> Source:
    raw_bytes = path.read_bytes()
    text = raw_bytes.decode("utf-8", errors="replace")
    return Source(
        kind=kind,
        raw_bytes=raw_bytes,
        content_text=text,
        content_hash=_hash(kind, raw_bytes),
        origin=str(path),
    )


def load_source(source_input: str, mineru_token: str | None = None) -> Source:
    """Load and normalize a source from a path, URL, or arxiv identifier."""
    try:
        source_input = source_input.strip()

        if _is_arxiv(source_input):
            return _load_arxiv_or_pdf(source_input, "arxiv", mineru_token=mineru_token)

        if source_input.startswith(("http://", "https://")):
            if source_input.lower().split("?", 1)[0].endswith(".pdf"):
                return _load_arxiv_or_pdf(source_input, "pdf", mineru_token=mineru_token)
            return _load_html(source_input)

        path = Path(source_input)
        if path.exists() and path.is_file():
            suffix = path.suffix.lower()
            if suffix == ".pdf":
                return _load_arxiv_or_pdf(source_input, "pdf", mineru_token=mineru_token)
            if suffix == ".md":
                return _load_local_file(path, "markdown")
            if suffix == ".txt":
                return _load_local_file(path, "text")
            raise IngestError(f"Unsupported file type: {suffix!r}")

        raise IngestError(f"Cannot resolve source: {source_input!r}")
    except IngestError:
        raise
    except Exception as exc:
        raise IngestError(f"Failed to ingest {source_input!r}: {exc}") from exc
