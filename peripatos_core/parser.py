"""PDF parser abstraction with pluggable document parsing backends."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
import importlib
from pathlib import Path
from typing import Any, Protocol

from peripatos_core.exceptions import ParseError


@dataclass
class ParsedPaper:
    """Result of parsing a PDF."""
    markdown: str
    sections: list[str] = field(default_factory=list)  # section headings found
    full_text: str = ""  # plain text fallback


def _extract_sections(markdown: str) -> list[str]:
    return [line.lstrip("#").strip() for line in markdown.splitlines() if line.startswith("#")]


def _coerce_sections(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, Iterable):
        return [str(item) for item in value]
    return [str(value)]


class DocumentParserBackend(Protocol):
    """Common interface for PDF parser backends."""

    def parse(self, pdf_path: Path) -> ParsedPaper:
        """Parse PDF file and return normalized ParsedPaper."""


class DoclingPDFParserBackend:
    """Docling-backed parser implementation."""

    def __init__(self) -> None:
        # Docling downloads model weights on first use; DOCLING_CACHE_DIR controls location
        self._converter = None  # lazy init to avoid slow import at module load

    def _get_converter(self):
        if self._converter is None:
            try:
                from docling.document_converter import DocumentConverter

                self._converter = DocumentConverter()
            except ImportError as exc:
                raise ParseError("docling is not installed") from exc
        return self._converter

    def parse(self, pdf_path: Path) -> ParsedPaper:
        try:
            converter = self._get_converter()
            result = converter.convert(str(pdf_path))
            doc = result.document
            markdown = doc.export_to_markdown()
            sections = _extract_sections(markdown)
            full_text = doc.export_to_text() if hasattr(doc, "export_to_text") else markdown
            return ParsedPaper(markdown=markdown, sections=sections, full_text=full_text)
        except Exception as exc:
            raise ParseError(f"Docling failed to parse {pdf_path}: {exc}") from exc


class MinerUPDFParserBackend:
    """MinerU-backed parser implementation."""

    def __init__(self) -> None:
        self._module = None

    def _get_module(self):
        if self._module is None:
            try:
                self._module = importlib.import_module("mineru")
            except ImportError as exc:
                raise ParseError("mineru is not installed") from exc
        return self._module

    def _call_parser(self, pdf_path: Path) -> Any:
        module = self._get_module()
        if hasattr(module, "parse_pdf"):
            return module.parse_pdf(str(pdf_path))
        if hasattr(module, "MinerUParser"):
            return module.MinerUParser().parse(str(pdf_path))
        if hasattr(module, "MinerU"):
            return module.MinerU().parse(str(pdf_path))
        raise ParseError(
            "mineru does not expose a supported parser API "
            "(expected parse_pdf, MinerUParser.parse, or MinerU.parse)"
        )

    def parse(self, pdf_path: Path) -> ParsedPaper:
        try:
            result = self._call_parser(pdf_path)

            if isinstance(result, dict):
                markdown = result.get("markdown") or result.get("text") or ""
                sections = _coerce_sections(result.get("sections"))
                full_text = result.get("full_text") or result.get("text") or markdown
            elif isinstance(result, str):
                markdown = result
                sections = _extract_sections(result)
                full_text = result
            else:
                markdown = (
                    result.export_to_markdown()
                    if hasattr(result, "export_to_markdown")
                    else getattr(result, "markdown", "")
                )
                full_text = (
                    result.export_to_text()
                    if hasattr(result, "export_to_text")
                    else getattr(result, "full_text", markdown)
                )
                sections = _coerce_sections(getattr(result, "sections", []))

            if not sections:
                sections = _extract_sections(markdown)

            return ParsedPaper(markdown=markdown, sections=sections, full_text=full_text)
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError(f"MinerU failed to parse {pdf_path}: {exc}") from exc


class PDFParser:
    """Parses a PDF using a configurable backend and returns structured text."""

    _BACKENDS = {
        "docling": DoclingPDFParserBackend,
        "mineru": MinerUPDFParserBackend,
    }

    def __init__(self, backend: str = "docling") -> None:
        self.backend = backend.lower()
        backend_cls = self._BACKENDS.get(self.backend)
        if backend_cls is None:
            supported = ", ".join(sorted(self._BACKENDS))
            raise ParseError(f"Unknown parser backend: {backend!r}. Supported: {supported}")
        self._backend: DocumentParserBackend = backend_cls()

    def parse(self, pdf_path: Path) -> ParsedPaper:
        """Parse a PDF and return structured content."""
        if not pdf_path.exists():
            raise ParseError(f"PDF not found: {pdf_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise ParseError(f"Expected .pdf file, got: {pdf_path.suffix}")
        return self._backend.parse(pdf_path)
