"""Tests for PaperFetcher."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from peripatos_core.fetcher import PaperFetcher, ARXIV_ID_RE, ARXIV_URL_RE
from peripatos_core.exceptions import FetchError
from peripatos_core.types import PaperMetadata


def test_arxiv_id_regex_matches():
    assert ARXIV_ID_RE.match("1706.03762")
    assert ARXIV_ID_RE.match("2301.00001v2")
    assert not ARXIV_ID_RE.match("not-an-id")


def test_arxiv_url_regex_extracts_id():
    m = ARXIV_URL_RE.search("https://arxiv.org/abs/1706.03762")
    assert m and m.group(1) == "1706.03762"
    m2 = ARXIV_URL_RE.search("https://arxiv.org/pdf/2301.00001v2")
    assert m2 and m2.group(1) == "2301.00001v2"


def test_fetch_local_pdf(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake")
    fetcher = PaperFetcher(output_dir=tmp_path)
    path, meta = fetcher.fetch(str(pdf))
    assert path == pdf
    assert meta.title == "paper"


def test_fetch_nonexistent_local_raises(tmp_path):
    fetcher = PaperFetcher(output_dir=tmp_path)
    with pytest.raises(FetchError):
        fetcher.fetch("/nonexistent/path/paper.pdf")


def test_fetch_unknown_source_raises(tmp_path):
    fetcher = PaperFetcher(output_dir=tmp_path)
    with pytest.raises(FetchError, match="Cannot resolve"):
        fetcher.fetch("not-a-valid-source")


def test_fetch_arxiv_id_calls_url(tmp_path):
    fetcher = PaperFetcher(output_dir=tmp_path)
    fetcher.request_delay_s = 0
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.iter_content = MagicMock(return_value=[b"%PDF-1.4 fake"])
    with patch("peripatos_core.fetcher.requests.get", return_value=mock_resp) as mock_get:
        path, meta = fetcher.fetch("1706.03762")
    assert mock_get.called
    assert "1706.03762" in mock_get.call_args[0][0]
    assert meta.arxiv_id == "1706.03762"
    assert path.exists()


def test_fetch_url_network_error(tmp_path):
    import requests as req
    fetcher = PaperFetcher(output_dir=tmp_path)
    with patch("peripatos_core.fetcher.requests.get", side_effect=req.ConnectionError("fail")):
        with pytest.raises(FetchError, match="Failed to download"):
            fetcher.fetch("https://example.com/paper.pdf")
