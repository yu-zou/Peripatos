from pathlib import Path

import pytest

from peripatos.eye.parser import PDFParser, ParsingError
from peripatos.models import SectionType


class _StubDocument:
    def __init__(self, markdown: str) -> None:
        self._markdown = markdown

    def export_to_markdown(self) -> str:
        return self._markdown


class _StubResult:
    def __init__(self, markdown: str) -> None:
        self.document = _StubDocument(markdown)


def _make_stub_converter(markdown: str):
    class _StubConverter:
        def __init__(self, pipeline_options=None) -> None:
            self.pipeline_options = pipeline_options

        def convert(self, source: str | Path) -> _StubResult:
            return _StubResult(markdown)

    return _StubConverter


def test_parse_valid_pdf_metadata(sample_pdf_path, sample_markdown, monkeypatch):
    parser = PDFParser(converter=_make_stub_converter(sample_markdown)())
    metadata = parser.parse(sample_pdf_path)

    assert metadata.title
    assert metadata.source_path == sample_pdf_path
    assert metadata.sections
    assert any(section.title for section in metadata.sections)


def test_section_classification(sample_pdf_path, sample_markdown, monkeypatch):
    parser = PDFParser(converter=_make_stub_converter(sample_markdown)())
    metadata = parser.parse(sample_pdf_path)

    section_map = {section.title.lower(): section.section_type for section in metadata.sections}
    assert section_map.get("abstract") == SectionType.ABSTRACT
    assert section_map.get("1. introduction") == SectionType.INTRODUCTION
    assert section_map.get("2. methodology") == SectionType.METHODOLOGY
    assert section_map.get("3. experiments") == SectionType.EXPERIMENTS
    assert section_map.get("4. conclusion") == SectionType.CONCLUSION
    assert section_map.get("references") == SectionType.REFERENCES


def test_invalid_path_raises_parsing_error(monkeypatch):
    parser = PDFParser(converter=_make_stub_converter("# Title")())

    with pytest.raises(ParsingError):
        parser.parse("/nonexistent/paper.pdf")


def test_markdown_preserves_latex(sample_pdf_path, sample_markdown, monkeypatch):
    parser = PDFParser(converter=_make_stub_converter(sample_markdown)())
    metadata = parser.parse(sample_pdf_path)

    combined_markdown = "\n".join(section.content for section in metadata.sections)
    assert "$" in combined_markdown or "\\" in combined_markdown
