"""Paper fetcher — resolves ArXiv ID, URL, or local path to a local PDF file."""
from __future__ import annotations
import re
import time
import tempfile
from pathlib import Path
import requests
from peripatos_core.exceptions import FetchError
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
        """Fetch a paper and return (local_pdf_path, metadata).

        Args:
            source: ArXiv ID (e.g. "1706.03762"), ArXiv URL, arbitrary PDF URL,
                    or local file path.

        Returns:
            Tuple of (path to local PDF, PaperMetadata).
        """
        source = source.strip()

        # Local file
        local = Path(source)
        if local.exists() and local.suffix.lower() == ".pdf":
            return local, PaperMetadata(title=local.stem, source_url=str(local))

        # ArXiv ID
        if ARXIV_ID_RE.match(source):
            return self._fetch_arxiv(source)

        # ArXiv URL
        m = ARXIV_URL_RE.search(source)
        if m:
            return self._fetch_arxiv(m.group(1))

        # Generic URL
        if source.startswith("http://") or source.startswith("https://"):
            return self._fetch_url(source, PaperMetadata(title="paper"))

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

    def _fetch_url(self, url: str, metadata: PaperMetadata) -> tuple[Path, PaperMetadata]:
        try:
            resp = requests.get(url, timeout=60, stream=True)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise FetchError(f"Failed to download {url}: {exc}") from exc

        suffix = ".pdf"
        tmp = tempfile.NamedTemporaryFile(
            dir=self._output_dir, suffix=suffix, delete=False
        )
        try:
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)
        finally:
            tmp.close()
        return Path(tmp.name), metadata
