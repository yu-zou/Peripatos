"""PDF parser wrapping Docling for text and section extraction."""
from __future__ import annotations
import os
from dataclasses import dataclass, field
from pathlib import Path
from peripatos_core.exceptions import ParseError


@dataclass
class ParsedPaper:
    """Result of parsing a PDF."""
    markdown: str
    sections: list[str] = field(default_factory=list)  # section headings found
    full_text: str = ""  # plain text fallback


class PDFParser:
    """Parses a PDF using Docling and returns structured text."""

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
            converter = self._get_converter()
            result = converter.convert(str(pdf_path))
            doc = result.document
            markdown = doc.export_to_markdown()
            # Extract section headings (lines starting with #)
            sections = [
                line.lstrip("#").strip()
                for line in markdown.splitlines()
                if line.startswith("#")
            ]
            full_text = doc.export_to_text() if hasattr(doc, "export_to_text") else markdown
            return ParsedPaper(markdown=markdown, sections=sections, full_text=full_text)
        except ParseError:
            raise
        except Exception as exc:
            raise ParseError(f"Docling failed to parse {pdf_path}: {exc}") from exc
