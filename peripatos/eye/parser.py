from __future__ import annotations

import importlib
import os
import re
from pathlib import Path
from typing import Any

from peripatos.models import PaperMetadata, SectionInfo, SectionType


class ParsingError(Exception):
    pass


class PDFParser:
    def __init__(self, converter: Any | None = None, use_vlm: bool = False) -> None:
        self._converter: Any | None = converter
        self._use_vlm = use_vlm

    def parse(self, source: str | Path) -> PaperMetadata:
        source_path = Path(source)
        if not source_path.exists() or not source_path.is_file():
            raise ParsingError(f"PDF not found: {source_path}")
        if self._converter is None:
            if self._use_vlm:
                from peripatos.eye.vlm import create_vlm_converter
                self._converter = create_vlm_converter()
            else:
                self._converter = _build_converter()
        if self._converter is None:
            raise ParsingError("Docling converter not available")

        try:
            result = self._converter.convert(source_path)
            markdown = result.document.export_to_markdown()
        except Exception as exc:
            raise ParsingError(f"Failed to parse PDF: {source_path}") from exc

        title = _extract_title(markdown)
        if not title:
            title = source_path.stem

        authors = _extract_authors(markdown)
        sections = _split_sections(markdown)
        abstract = _extract_abstract(sections)

        return PaperMetadata(
            title=title,
            authors=authors,
            abstract=abstract,
            source_path=source_path,
            sections=sections,
        )


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")


def _load_docling() -> tuple[Any, Any, Any, Any]:
    document_module = importlib.import_module("docling.document_converter")
    options_module = importlib.import_module("docling.datamodel.pipeline_options")
    base_module = importlib.import_module("docling.datamodel.base_models")
    return (
        document_module.DocumentConverter,
        options_module.PdfPipelineOptions,
        document_module.PdfFormatOption,
        base_module.InputFormat,
    )


def _build_converter() -> Any | None:
    if os.environ.get("PERIPATOS_SKIP_DOCLING"):
        return None
    try:
        document_converter, pdf_options, pdf_format_option, input_format = _load_docling()
        options = pdf_options(
            do_formula_enrichment=True,
            do_table_structure=True,
            do_ocr=True,
        )
        format_options = {input_format.PDF: pdf_format_option(pipeline_options=options)}
        return document_converter(format_options=format_options)
    except Exception:
        return None


def _extract_title(markdown: str) -> str:
    for line in markdown.splitlines():
        match = _HEADING_RE.match(line)
        if match and match.group(1) == "#":
            return match.group(2).strip()
    return ""


def _extract_authors(markdown: str) -> list[str]:
    lines = markdown.splitlines()[:30]
    author_line = None
    for line in lines:
        if "author" in line.lower():
            author_line = line
            break

    if not author_line:
        return []

    cleaned = re.sub(r"[*_`]", "", author_line)
    cleaned = re.sub(r"(?i)authors?:", "", cleaned).strip()
    if not cleaned:
        return []

    parts = re.split(r",| and ", cleaned)
    return [part.strip() for part in parts if part.strip()]


def _split_sections(markdown: str) -> list[SectionInfo]:
    sections: list[SectionInfo] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in markdown.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            if current_title is not None:
                sections.append(
                    SectionInfo(
                        title=current_title,
                        content="\n".join(current_lines).strip(),
                        section_type=_classify_section(current_title),
                    )
                )
            current_title = match.group(2).strip()
            current_lines = [line]
        elif current_title is not None:
            current_lines.append(line)

    if current_title is not None:
        sections.append(
            SectionInfo(
                title=current_title,
                content="\n".join(current_lines).strip(),
                section_type=_classify_section(current_title),
            )
        )

    return sections


def _classify_section(title: str) -> SectionType:
    lowered = title.lower()
    if "abstract" in lowered:
        return SectionType.ABSTRACT
    if "introduction" in lowered or "intro" in lowered:
        return SectionType.INTRODUCTION
    if "method" in lowered or "approach" in lowered:
        return SectionType.METHODOLOGY
    if "experiment" in lowered or "evaluation" in lowered:
        return SectionType.EXPERIMENTS
    if "result" in lowered:
        return SectionType.RESULTS
    if "discussion" in lowered:
        return SectionType.DISCUSSION
    if "conclusion" in lowered:
        return SectionType.CONCLUSION
    if "reference" in lowered or "bibliography" in lowered:
        return SectionType.REFERENCES
    return SectionType.OTHER


def _extract_abstract(sections: list[SectionInfo]) -> str:
    for section in sections:
        if section.section_type == SectionType.ABSTRACT:
            return _strip_heading(section.content)
    return ""


def _strip_heading(content: str) -> str:
    lines = content.splitlines()
    if lines and _HEADING_RE.match(lines[0]):
        return "\n".join(lines[1:]).strip()
    return content.strip()
