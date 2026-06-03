"""Tests for RAG source ingestion."""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from peripatos_core.rag.sources import load_source, _load_arxiv_or_pdf


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