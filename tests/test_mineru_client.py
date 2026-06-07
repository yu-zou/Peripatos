"""Comprehensive unit tests for MinerUClient."""
import io
import json
import zipfile

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from peripatos_core.mineru_client import MinerUClient, MinerUResult


def _make_sample_pdf(tmp_path: Path, name: str = "paper.pdf") -> Path:
    pdf = tmp_path / name
    pdf.write_bytes(
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"trailer<</Size 4/Root 1 0 R>>\n%%EOF"
    )
    return pdf


def _create_sample_zip(markdown: str = "# Test", content_list: list | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("full.md", markdown)
        if content_list is not None:
            zf.writestr("content_list.json", json.dumps(content_list))
    return buf.getvalue()


class TestClientInit:
    def test_no_token(self):
        client = MinerUClient()
        assert client._token is None

    def test_with_token(self):
        client = MinerUClient(token="my-token")
        assert client._token == "my-token"


class TestFlashUploadInit:
    def test_success(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()

        with patch("peripatos_core.mineru_client.requests.post") as mock_post, \
             patch("peripatos_core.mineru_client.requests.put") as mock_put, \
             patch("peripatos_core.mineru_client.requests.get") as mock_get, \
             patch("peripatos_core.mineru_client.time.sleep"), \
             patch("peripatos_core.mineru_client.time.time", return_value=100.0):

            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = {
                "code": 0,
                "data": {"task_id": "task-1", "file_url": "https://upload.example.com/file"},
            }

            mock_put.return_value = MagicMock()

            poll_resp = MagicMock()
            poll_resp.json.return_value = {
                "code": 0,
                "data": {"state": "done", "markdown_url": "https://dl.example.com/md"},
            }
            md_resp = MagicMock()
            md_resp.text = "# Hello Flash"
            mock_get.side_effect = [poll_resp, md_resp]

            result = client.flash_extract(pdf)

        assert isinstance(result, MinerUResult)
        assert mock_post.call_count == 1
        call_args = mock_post.call_args
        assert "/parse/file" in call_args[0][0]
        sent_json = call_args.kwargs.get("json", {})
        assert sent_json.get("file_name") == "paper.pdf"

    def test_api_error(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()

        with patch("peripatos_core.mineru_client.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = {
                "code": 1,
                "msg": "File name is required",
            }

            with pytest.raises(RuntimeError, match="File name is required"):
                client.flash_extract(pdf)


class TestBatchUploadURL:
    def test_success(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient(token="test-token")

        with patch("peripatos_core.mineru_client.requests.post") as mock_post, \
             patch("peripatos_core.mineru_client.requests.put") as mock_put, \
             patch("peripatos_core.mineru_client.requests.get") as mock_get, \
             patch("peripatos_core.mineru_client.time.sleep"), \
             patch("peripatos_core.mineru_client.time.time", return_value=2000000000.0):

            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = {
                "code": 0,
                "data": {
                    "batch_id": "batch-1",
                    "file_urls": ["https://upload.example.com/batch-file"],
                },
            }

            mock_put.return_value = MagicMock()

            poll_resp = MagicMock()
            poll_resp.json.return_value = {
                "code": 0,
                "data": {
                    "batch_id": "batch-1",
                    "extract_result": [{
                        "state": "done",
                        "full_zip_url": "https://dl.example.com/result.zip",
                    }],
                },
            }

            zip_content = _create_sample_zip("# Precision Result")
            zip_resp = MagicMock()
            zip_resp.content = zip_content
            mock_get.side_effect = [poll_resp, zip_resp]

            result = client.extract(pdf)

        assert isinstance(result, MinerUResult)
        assert mock_post.call_count == 1
        call_args = mock_post.call_args
        assert "/file-urls/batch" in call_args[0][0]
        sent_json = call_args.kwargs.get("json", {})
        assert sent_json["files"][0]["name"] == "paper.pdf"
        assert sent_json["model_version"] == "vlm"
        assert "Authorization" in call_args.kwargs.get("headers", {})

    def test_no_urls_raises_error(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient(token="test-token")

        with patch("peripatos_core.mineru_client.requests.post") as mock_post:
            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = {
                "code": 0,
                "data": {"batch_id": "batch-1", "file_urls": []},
            }

            with pytest.raises(RuntimeError, match="No upload URL returned"):
                client.extract(pdf)


class TestFlashExtract:
    def test_success(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()

        with patch("peripatos_core.mineru_client.requests.post") as mock_post, \
             patch("peripatos_core.mineru_client.requests.put") as mock_put, \
             patch("peripatos_core.mineru_client.requests.get") as mock_get, \
             patch("peripatos_core.mineru_client.time.sleep"), \
             patch("peripatos_core.mineru_client.time.time", return_value=100.0):

            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = {
                "code": 0,
                "data": {"task_id": "task-1", "file_url": "https://upload.example.com/file"},
            }

            mock_put.return_value = MagicMock()

            poll_resp = MagicMock()
            poll_resp.json.return_value = {
                "code": 0,
                "data": {"state": "done", "markdown_url": "https://dl.example.com/md"},
            }

            expected_md = "# Abstract\n\nHello world.\n\n## Methods\n\nMethods text."
            md_resp = MagicMock()
            md_resp.text = expected_md
            mock_get.side_effect = [poll_resp, md_resp]

            result = client.flash_extract(pdf)

        assert isinstance(result, MinerUResult)
        assert result.markdown == expected_md
        assert "Hello world" in result.markdown
        assert "Abstract" in result.sections
        assert "Methods" in result.sections

    def test_task_failed(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()

        with patch("peripatos_core.mineru_client.requests.post") as mock_post, \
             patch("peripatos_core.mineru_client.requests.put") as mock_put, \
             patch("peripatos_core.mineru_client.requests.get") as mock_get, \
             patch("peripatos_core.mineru_client.time.sleep"), \
             patch("peripatos_core.mineru_client.time.time", return_value=100.0):

            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = {
                "code": 0,
                "data": {"task_id": "task-1", "file_url": "https://upload.example.com/file"},
            }

            mock_put.return_value = MagicMock()

            poll_resp = MagicMock()
            poll_resp.json.return_value = {
                "code": 0,
                "data": {"state": "failed", "err_msg": "File too large"},
            }
            mock_get.return_value = poll_resp

            with pytest.raises(RuntimeError, match="MinerU Flash task failed: File too large"):
                client.flash_extract(pdf)

    def test_poll_timeout(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()

        with patch("peripatos_core.mineru_client.requests.post") as mock_post, \
             patch("peripatos_core.mineru_client.requests.put") as mock_put, \
             patch("peripatos_core.mineru_client.requests.get") as mock_get, \
             patch("peripatos_core.mineru_client.time.sleep"):

            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = {
                "code": 0,
                "data": {"task_id": "task-1", "file_url": "https://upload.example.com/file"},
            }

            mock_put.return_value = MagicMock()

            poll_resp = MagicMock()
            poll_resp.json.return_value = {
                "code": 0,
                "data": {"state": "running"},
            }
            mock_get.return_value = poll_resp

            with patch("peripatos_core.mineru_client.time.time") as mock_time:
                mock_time.side_effect = [100.0, 135.0]
                with pytest.raises(TimeoutError, match="Flash task did not complete"):
                    client.flash_extract(pdf, timeout=30)

    def test_no_markdown_url(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()

        with patch("peripatos_core.mineru_client.requests.post") as mock_post, \
             patch("peripatos_core.mineru_client.requests.put") as mock_put, \
             patch("peripatos_core.mineru_client.requests.get") as mock_get, \
             patch("peripatos_core.mineru_client.time.sleep"), \
             patch("peripatos_core.mineru_client.time.time", return_value=100.0):

            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = {
                "code": 0,
                "data": {"task_id": "task-1", "file_url": "https://upload.example.com/file"},
            }

            mock_put.return_value = MagicMock()

            poll_resp = MagicMock()
            poll_resp.json.return_value = {
                "code": 0,
                "data": {"state": "done"},
            }
            mock_get.return_value = poll_resp

            with pytest.raises(RuntimeError, match="no markdown_url"):
                client.flash_extract(pdf)


class TestPrecisionExtract:
    def test_success(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient(token="test-token")

        with patch("peripatos_core.mineru_client.requests.post") as mock_post, \
             patch("peripatos_core.mineru_client.requests.put") as mock_put, \
             patch("peripatos_core.mineru_client.requests.get") as mock_get, \
             patch("peripatos_core.mineru_client.time.sleep"), \
             patch("peripatos_core.mineru_client.time.time", return_value=2000000000.0):

            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = {
                "code": 0,
                "data": {
                    "batch_id": "batch-1",
                    "file_urls": ["https://upload.example.com/batch-file"],
                },
            }

            mock_put.return_value = MagicMock()

            poll_resp = MagicMock()
            poll_resp.json.return_value = {
                "code": 0,
                "data": {
                    "batch_id": "batch-1",
                    "extract_result": [{
                        "state": "done",
                        "full_zip_url": "https://dl.example.com/result.zip",
                    }],
                },
            }

            zip_content = _create_sample_zip(
                markdown="# Precision Test\n\nContent here.",
                content_list=[
                    {"text": "Precision Test", "text_level": 1},
                    {"text": "Content here.", "text_level": 0},
                ],
            )
            zip_resp = MagicMock()
            zip_resp.content = zip_content
            mock_get.side_effect = [poll_resp, zip_resp]

            result = client.extract(pdf)

        assert isinstance(result, MinerUResult)
        assert "Precision Test" in result.markdown
        assert "Content here" in result.markdown
        assert result.sections == ["Precision Test"]

    def test_requires_token(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()

        with pytest.raises(RuntimeError, match="requires an API token"):
            client.extract(pdf)

    def test_task_failed(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient(token="test-token")

        with patch("peripatos_core.mineru_client.requests.post") as mock_post, \
             patch("peripatos_core.mineru_client.requests.put") as mock_put, \
             patch("peripatos_core.mineru_client.requests.get") as mock_get, \
             patch("peripatos_core.mineru_client.time.sleep"), \
             patch("peripatos_core.mineru_client.time.time", return_value=100.0):

            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = {
                "code": 0,
                "data": {
                    "batch_id": "batch-1",
                    "file_urls": ["https://upload.example.com/batch-file"],
                },
            }

            mock_put.return_value = MagicMock()

            poll_resp = MagicMock()
            poll_resp.json.return_value = {
                "code": 0,
                "data": {
                    "extract_result": [{
                        "state": "failed",
                        "err_msg": "Document parsing failed",
                    }],
                },
            }
            mock_get.return_value = poll_resp

            with pytest.raises(RuntimeError, match="MinerU Precision task failed: Document parsing failed"):
                client.extract(pdf)

    def test_poll_timeout(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient(token="test-token")

        with patch("peripatos_core.mineru_client.requests.post") as mock_post, \
             patch("peripatos_core.mineru_client.requests.put") as mock_put, \
             patch("peripatos_core.mineru_client.requests.get") as mock_get, \
             patch("peripatos_core.mineru_client.time.sleep"):

            mock_post.return_value = MagicMock()
            mock_post.return_value.json.return_value = {
                "code": 0,
                "data": {
                    "batch_id": "batch-1",
                    "file_urls": ["https://upload.example.com/batch-file"],
                },
            }

            mock_put.return_value = MagicMock()

            poll_resp = MagicMock()
            poll_resp.json.return_value = {
                "code": 0,
                "data": {
                    "extract_result": [{"state": "running"}],
                },
            }
            mock_get.return_value = poll_resp

            with patch("peripatos_core.mineru_client.time.time") as mock_time:
                mock_time.side_effect = [100.0, 135.0]
                with pytest.raises(TimeoutError, match="Precision task did not complete"):
                    client.extract(pdf, timeout=30)


class TestHelpers:
    def test_check_api_error_success(self):
        MinerUClient._check_api_error({"code": 0})

    def test_check_api_error_failure(self):
        with pytest.raises(RuntimeError, match="Invalid file format"):
            MinerUClient._check_api_error({"code": 1, "msg": "Invalid file format"})

    def test_check_api_error_no_msg(self):
        with pytest.raises(RuntimeError, match="Unknown error"):
            MinerUClient._check_api_error({"code": 1})

    def test_extract_sections_from_content_list(self):
        content_list = [
            {"text": "Intro", "text_level": 1},
            {"text": "Body text", "text_level": 0},
            {"text": "Methods", "text_level": 2},
        ]
        result = MinerUClient._extract_sections_from_markdown(
            "# Ignored\n\nBody text\n\n## Methods", content_list
        )
        assert result == ["Intro", "Methods"]

    def test_extract_sections_fallback_to_markdown(self):
        markdown = "# Abstract\n\nText.\n\n## Results\n\nData."
        result = MinerUClient._extract_sections_from_markdown(markdown, [])
        assert result == ["Abstract", "Results"]

    def test_extract_sections_empty_both(self):
        result = MinerUClient._extract_sections_from_markdown("", [])
        assert result == []

    def test_extract_sections_strips_leading_pound_signs(self):
        markdown = "#  Leading space  \n###  Triple hash  "
        result = MinerUClient._extract_sections_from_markdown(markdown, [])
        assert result == ["Leading space", "Triple hash"]


class TestContentListHelpers:
    def test_content_list_present(self):
        content_list_data = [
            {"text": "Title", "text_level": 1},
            {"text": "Paragraph", "text_level": 0},
        ]
        zip_content = _create_sample_zip("# Title\n\nParagraph", content_list=content_list_data)
        headers = {"Accept": "application/json"}

        with patch("peripatos_core.mineru_client.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.content = zip_content
            mock_get.return_value = mock_resp

            markdown, content_list = MinerUClient._download_and_extract_zip(
                "https://example.com/result.zip", headers
            )

        assert markdown == "# Title\n\nParagraph"
        assert content_list == content_list_data

    def test_content_list_absent(self):
        zip_content = _create_sample_zip("# Only Markdown\n\nNo JSON.")
        headers = {"Accept": "application/json"}

        with patch("peripatos_core.mineru_client.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.content = zip_content
            mock_get.return_value = mock_resp

            markdown, content_list = MinerUClient._download_and_extract_zip(
                "https://example.com/result.zip", headers
            )

        assert markdown == "# Only Markdown\n\nNo JSON."
        assert content_list == []
