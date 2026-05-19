"""Tests for PDFParser."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from peripatos_core.parser import PDFParser, ParsedPaper
from peripatos_core.exceptions import ParseError


def _make_mock_converter(markdown: str = "# Title\n\nSome text."):
    """Build a mock Docling DocumentConverter."""
    mock_doc = MagicMock()
    mock_doc.export_to_markdown.return_value = markdown
    mock_doc.export_to_text.return_value = "Some text."
    mock_result = MagicMock()
    mock_result.document = mock_doc
    mock_converter = MagicMock()
    mock_converter.convert.return_value = mock_result
    return mock_converter


def test_parse_returns_parsed_paper(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    parser = PDFParser()
    parser._converter = _make_mock_converter("# Introduction\n\nHello world.")
    result = parser.parse(pdf)
    assert isinstance(result, ParsedPaper)
    assert "Introduction" in result.sections
    assert "Hello world" in result.markdown


def test_parse_missing_file_raises(tmp_path):
    parser = PDFParser()
    with pytest.raises(ParseError, match="not found"):
        parser.parse(tmp_path / "missing.pdf")


def test_parse_non_pdf_raises(tmp_path):
    txt = tmp_path / "paper.txt"
    txt.write_text("not a pdf")
    parser = PDFParser()
    with pytest.raises(ParseError, match="Expected .pdf"):
        parser.parse(txt)


def test_parse_extracts_sections(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    parser = PDFParser()
    parser._converter = _make_mock_converter(
        "# Abstract\n\nText.\n## Introduction\n\nMore text.\n### Related Work\n\nEven more."
    )
    result = parser.parse(pdf)
    assert "Abstract" in result.sections
    assert "Introduction" in result.sections
    assert "Related Work" in result.sections


def test_parse_docling_error_raises(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    parser = PDFParser()
    mock_converter = MagicMock()
    mock_converter.convert.side_effect = RuntimeError("docling internal error")
    parser._converter = mock_converter
    with pytest.raises(ParseError, match="Docling failed"):
        parser.parse(pdf)


def test_parse_real_fixture():
    """Smoke test with the real sample PDF fixture (no mocking, requires Docling models)."""
    import os
    if not os.environ.get("RUN_INTEGRATION"):
        pytest.skip("Skipped: set RUN_INTEGRATION=1 to run (requires Docling model download)")
    fixture = Path("tests/fixtures/sample_paper.pdf")
    if not fixture.exists():
        pytest.skip("sample_paper.pdf fixture not found")
    parser = PDFParser()
    result = parser.parse(fixture)
    assert len(result.markdown) > 100
    assert len(result.sections) > 0
