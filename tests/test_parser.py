"""Tests for PDFParser with MinerU + PyMuPDF fallback."""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from peripatos_core.parser import PDFParser, ParsedPaper
from peripatos_core.exceptions import ParseError


def _make_sample_pdf(tmp_path: Path, name: str = "paper.pdf") -> Path:
    """Create a minimal valid PDF file."""
    pdf = tmp_path / name
    pdf.write_bytes(
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"trailer<</Size 4/Root 1 0 R>>\n%%EOF"
    )
    return pdf


def test_mineru_success_returns_parsed_paper(tmp_path):
    parser = PDFParser(mineru_token="test-token")
    pdf = _make_sample_pdf(tmp_path)

    with patch("peripatos_core.mineru_client.MinerUClient.extract") as mock_extract:
        mock_extract.return_value = MagicMock(
            markdown="# Introduction\n\nHello world.",
            sections=["Introduction"],
        )
        result = parser.parse(pdf)

    assert isinstance(result, ParsedPaper)
    assert "Introduction" in result.sections
    assert "Hello world" in result.markdown
    mock_extract.assert_called_once()


def test_mineru_failure_falls_back_to_pymupdf(tmp_path):
    parser = PDFParser()
    pdf = _make_sample_pdf(tmp_path)

    with patch("peripatos_core.mineru_client.MinerUClient.extract") as mock_extract:
        mock_extract.side_effect = RuntimeError("API error")
        result = parser.parse(pdf)

    assert isinstance(result, ParsedPaper)
    assert mock_extract.called


def test_mineru_timeout_falls_back_to_pymupdf(tmp_path):
    parser = PDFParser()
    pdf = _make_sample_pdf(tmp_path)

    with patch("peripatos_core.mineru_client.MinerUClient.extract") as mock_extract:
        mock_extract.side_effect = TimeoutError("timed out")
        result = parser.parse(pdf)

    assert isinstance(result, ParsedPaper)


def test_parse_missing_file_raises():
    parser = PDFParser()
    with pytest.raises(ParseError, match="not found"):
        parser.parse(Path("/nonexistent/missing.pdf"))


def test_parse_non_pdf_raises(tmp_path):
    txt = tmp_path / "paper.txt"
    txt.write_text("not a pdf")
    parser = PDFParser()
    with pytest.raises(ParseError, match="Expected .pdf"):
        parser.parse(txt)


def test_mineru_extracts_sections_from_result(tmp_path):
    parser = PDFParser()
    pdf = _make_sample_pdf(tmp_path)

    with patch("peripatos_core.mineru_client.MinerUClient.extract") as mock_extract:
        mock_extract.return_value = MagicMock(
            markdown="# Abstract\n\nText.\n## Introduction\n\nMore.",
            sections=["Abstract", "Introduction"],
        )
        result = parser.parse(pdf)

    assert "Abstract" in result.sections
    assert "Introduction" in result.sections


def test_pymupdf_fallback_extracts_text(tmp_path):
    """When MinerU fails, PyMuPDF fallback is invoked and returns ParsedPaper."""
    parser = PDFParser()
    pdf = _make_sample_pdf(tmp_path)

    with patch("peripatos_core.mineru_client.MinerUClient.extract") as mock_extract:
        mock_extract.side_effect = RuntimeError("API down")
        with patch.object(PDFParser, "_parse_with_pymupdf") as mock_pymupdf:
            mock_pymupdf.return_value = ParsedPaper(
                markdown="fallback text", sections=[], full_text="fallback text"
            )
            result = parser.parse(pdf)

    assert isinstance(result, ParsedPaper)
    assert result.markdown == "fallback text"
    mock_pymupdf.assert_called_once()


def test_both_fail_raises_parse_error(tmp_path):
    """When both MinerU and PyMuPDF fail, ParseError is raised."""
    parser = PDFParser()
    pdf = _make_sample_pdf(tmp_path)

    with patch("peripatos_core.mineru_client.MinerUClient.extract") as mock_mineru:
        mock_mineru.side_effect = RuntimeError("API down")
        with patch.dict("sys.modules", {"pymupdf": None}):
            with pytest.raises(ParseError, match="PyMuPDF is not installed|PyMuPDF failed"):
                parser.parse(pdf)
