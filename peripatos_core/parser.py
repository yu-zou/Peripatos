"""PDF parser wrapping MinerU cloud API with PyMuPDF fallback."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
import requests
from pathlib import Path

from peripatos_core.exceptions import ParseError
from peripatos_core.mineru_client import MinerUClient

logger = logging.getLogger(__name__)


@dataclass
class ParsedPaper:
    """Result of parsing a PDF."""
    markdown: str
    sections: list[str] = field(default_factory=list)
    full_text: str = ""


class PDFParser:
    """Parses a PDF using MinerU cloud API, falling back to PyMuPDF.

    MinerU requires network access and provides high-quality extraction
    (tables, formulas, headings). On any failure, PyMuPDF is used as
    a lightweight fallback (text-only, no ML).
    """

    def __init__(self, mineru_token: str | None = None) -> None:
        self._mineru_token = mineru_token

    def parse(self, pdf_path: Path) -> ParsedPaper:
        """Parse a PDF and return structured content.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            ParsedPaper with markdown text and section headings.
        """
        if not pdf_path.exists():
            raise ParseError(f"PDF not found: {pdf_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise ParseError(f"Expected .pdf file, got: {pdf_path.suffix}")

        try:
            client = MinerUClient(token=self._mineru_token)
            if self._mineru_token:
                result = client.extract(pdf_path)
            else:
                result = client.flash_extract(pdf_path)
            return ParsedPaper(
                markdown=result.markdown,
                sections=result.sections,
                full_text=result.markdown,
            )
        except (requests.RequestException, RuntimeError, TimeoutError, OSError) as exc:
            logger.warning(
                "MinerU API unavailable (%s), falling back to PyMuPDF. "
                "Tables and formulas will not be extracted.",
                exc,
            )

        return self._parse_with_pymupdf(pdf_path)

    @staticmethod
    def _parse_with_pymupdf(pdf_path: Path) -> ParsedPaper:
        """Parse PDF using PyMuPDF (lightweight, text-only)."""
        import warnings

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"builtin type \w+ has no __module__",
                    category=DeprecationWarning,
                )
                import pymupdf  # type: ignore[reportMissingImports]
        except ImportError as exc:
            raise ParseError("PyMuPDF is not installed") from exc

        try:
            doc = pymupdf.open(str(pdf_path))
            markdown_parts = []
            sections = []
            for page in doc:
                text = page.get_text()
                markdown_parts.append(text)
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped and (stripped.isupper() or stripped.startswith("#")):
                        sections.append(stripped.lstrip("#").strip())
            doc.close()

            markdown = "\n\n".join(markdown_parts)
            return ParsedPaper(
                markdown=markdown,
                sections=sections,
                full_text=markdown,
            )
        except Exception as exc:
            raise ParseError(f"PyMuPDF failed to parse {pdf_path}: {exc}") from exc
