"""Paper fetcher — resolves ArXiv ID, URL, or local path to a local file."""
from __future__ import annotations
import re
import time
import tempfile
from pathlib import Path
from urllib.parse import urlparse
import requests
from peripatos_core.exceptions import FetchError
from peripatos_core.http import request_with_retry
from peripatos_core.types import PaperMetadata

ARXIV_PDF_URL = "https://arxiv.org/pdf/{arxiv_id}.pdf"
ARXIV_ABS_URL = "https://arxiv.org/abs/{arxiv_id}"
ARXIV_ID_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
ARXIV_URL_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)")


class PaperFetcher:
    """Fetches papers from ArXiv, arbitrary URLs, or local filesystem."""

    request_delay_s: float = 3.0

    def __init__(self, output_dir: Path | None = None) -> None:
        self._output_dir = output_dir or Path(tempfile.gettempdir())

    def fetch(self, source: str) -> tuple[Path, PaperMetadata]:
        """Fetch a paper and return (local_path, metadata).

        Args:
            source: ArXiv ID (e.g. "1706.03762"), ArXiv URL, arbitrary PDF/HTML URL,
                    or local file path (.pdf, .md, .txt).

        Returns:
            Tuple of (path to local file, PaperMetadata).
        """
        source = source.strip()

        # Local file
        local = Path(source)
        if local.exists():
            suffix = local.suffix.lower()
            if suffix in (".pdf", ".md", ".txt"):
                return local, PaperMetadata(title=local.stem, source_url=str(local))

        # ArXiv ID
        if ARXIV_ID_RE.match(source):
            return self._fetch_arxiv(source)

        # ArXiv URL
        m = ARXIV_URL_RE.search(source)
        if m:
            return self._fetch_arxiv(m.group(1))

        # Generic URL — PDF or HTML
        if source.startswith("http://") or source.startswith("https://"):
            parsed_path = urlparse(source).path.lower()
            if parsed_path.endswith(".pdf"):
                return self._fetch_url(source, PaperMetadata(title="paper", source_url=source))
            return self._fetch_url(
                source,
                PaperMetadata(title=source, source_url=source),
                suffix=".html",
            )

        raise FetchError(f"Cannot resolve source: {source!r}")

    def _fetch_arxiv(self, arxiv_id: str) -> tuple[Path, PaperMetadata]:
        pdf_url = ARXIV_PDF_URL.format(arxiv_id=arxiv_id)
        metadata = PaperMetadata(
            title=f"ArXiv:{arxiv_id}",
            arxiv_id=arxiv_id,
            source_url=ARXIV_ABS_URL.format(arxiv_id=arxiv_id),
        )
        time.sleep(self.request_delay_s)
        return self._fetch_url(pdf_url, metadata)

    def _fetch_url(
        self,
        url: str,
        metadata: PaperMetadata,
        suffix: str = ".pdf",
    ) -> tuple[Path, PaperMetadata]:
        try:
            resp = request_with_retry("GET", url, timeout=60, stream=True)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise FetchError(f"Failed to download {url}: {exc}") from exc

        tmp = tempfile.NamedTemporaryFile(
            dir=self._output_dir, suffix=suffix, delete=False
        )
        try:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    tmp.write(chunk)
        except (
            requests.exceptions.ChunkedEncodingError,
            requests.exceptions.ConnectionError,
            requests.exceptions.SSLError,
        ) as exc:
            tmp.seek(0)
            tmp.truncate()
            raise FetchError(f"Streaming download failed for {url}: {exc}") from exc
        finally:
            tmp.close()
        return Path(tmp.name), metadata
