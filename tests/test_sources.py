"""Tests for RAG source ingestion."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from peripatos_core.rag.sources import load_source, _load_arxiv_or_pdf, _is_arxiv
from peripatos_core.exceptions import IngestError


def test_load_arxiv_or_pdf_passes_mineru_token(tmp_path):
    """_load_arxiv_or_pdf threads mineru_token to PDFParser."""
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake content")

    with patch("peripatos_core.rag.sources.PaperFetcher") as MockFetcher, \
         patch("peripatos_core.rag.sources.PDFParser") as MockParser:
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = (str(pdf), MagicMock(title="Test"))
        MockFetcher.return_value = mock_fetcher

        mock_parser = MagicMock()
        mock_parser.parse.return_value = MagicMock(markdown="content", full_text="content")
        MockParser.return_value = mock_parser

        _load_arxiv_or_pdf("2301.00001", "arxiv", mineru_token="my-secret-token")

        MockParser.assert_called_once_with(mineru_token="my-secret-token")


def test_load_arxiv_or_pdf_default_no_token(tmp_path):
    """_load_arxiv_or_pdf defaults to no mineru_token."""
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake content")

    with patch("peripatos_core.rag.sources.PaperFetcher") as MockFetcher, \
         patch("peripatos_core.rag.sources.PDFParser") as MockParser:
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = (str(pdf), MagicMock(title="Test"))
        MockFetcher.return_value = mock_fetcher

        mock_parser = MagicMock()
        mock_parser.parse.return_value = MagicMock(markdown="content", full_text="content")
        MockParser.return_value = mock_parser

        _load_arxiv_or_pdf("2301.00001", "arxiv")

        MockParser.assert_called_once_with(mineru_token=None)


def test_load_source_passes_token_to_pdf(tmp_path):
    """load_source threads mineru_token for PDF sources."""
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake content")

    with patch("peripatos_core.rag.sources.PaperFetcher") as MockFetcher, \
         patch("peripatos_core.rag.sources.PDFParser") as MockParser:
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = (str(pdf), MagicMock(title="Test"))
        MockFetcher.return_value = mock_fetcher

        mock_parser = MagicMock()
        mock_parser.parse.return_value = MagicMock(markdown="content", full_text="content")
        MockParser.return_value = mock_parser

        load_source(str(pdf), mineru_token="config-token")

        MockParser.assert_called_once_with(mineru_token="config-token")


def test_is_arxiv_with_id():
    assert _is_arxiv("2301.00001") is True


def test_is_arxiv_with_versioned_id():
    assert _is_arxiv("2301.00001v2") is True


def test_is_arxiv_with_url():
    assert _is_arxiv("https://arxiv.org/abs/2301.00001") is True


def test_is_arxiv_with_non_arxiv():
    assert _is_arxiv("not-an-id") is False


def test_is_arxiv_with_local_path():
    assert _is_arxiv("/path/to/paper.pdf") is False


def test_load_source_local_markdown_file(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text("# Hello\n\nWorld content")
    result = load_source(str(md_file))
    assert result.kind == "markdown"
    assert "Hello" in result.content_text
    assert "World content" in result.content_text


def test_load_source_local_text_file(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Hello World")
    result = load_source(str(txt_file))
    assert result.kind == "text"
    assert "Hello World" in result.content_text


def test_load_source_unsupported_extension_raises(tmp_path):
    file = tmp_path / "test.xyz"
    file.write_text("data")
    with pytest.raises(IngestError, match="Unsupported file type"):
        load_source(str(file))


def test_load_source_nonexistent_raises():
    with pytest.raises(IngestError):
        load_source("/nonexistent/path.pdf")


def test_load_source_pdf_passes_mineru_token(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake content")

    with patch("peripatos_core.rag.sources.PaperFetcher") as MockFetcher, \
         patch("peripatos_core.rag.sources.PDFParser") as MockParser:
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = (str(pdf), MagicMock(title="Test"))
        MockFetcher.return_value = mock_fetcher

        mock_parser = MagicMock()
        mock_parser.parse.return_value = MagicMock(markdown="content", full_text="content")
        MockParser.return_value = mock_parser

        load_source(str(pdf), mineru_token="pdf-token")

        MockParser.assert_called_once_with(mineru_token="pdf-token")