"""Comprehensive unit tests for MinerUClient."""
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


class TestMinerUResult:
    def test_construction(self):
        result = MinerUResult(markdown="# Hello", sections=["Hello"])
        assert result.markdown == "# Hello"
        assert result.sections == ["Hello"]

    def test_default_values_are_required(self):
        result = MinerUResult(markdown="", sections=[])
        assert result.markdown == ""
        assert result.sections == []

    def test_equality(self):
        a = MinerUResult(markdown="md", sections=["a", "b"])
        b = MinerUResult(markdown="md", sections=["a", "b"])
        c = MinerUResult(markdown="other", sections=["a", "b"])
        assert a == b
        assert a != c


class TestHeaders:
    def test_with_token(self):
        client = MinerUClient(token="my-token")
        headers = client._headers()
        assert headers["Accept"] == "application/json"
        assert headers["Authorization"] == "Bearer my-token"

    def test_without_token(self):
        client = MinerUClient()
        headers = client._headers()
        assert headers["Accept"] == "application/json"
        assert "Authorization" not in headers

    def test_none_token(self):
        client = MinerUClient(token=None)
        headers = client._headers()
        assert "Authorization" not in headers


class TestUploadFile:
    def test_success_with_file_id(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"file_id": "fid-123"}
            mock_post.return_value = mock_resp

            result = client._upload_file(pdf, {})

        assert result == "fid-123"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert "files" in call_kwargs

    def test_success_with_id_fallback(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"id": "fid-456"}
            mock_post.return_value = mock_resp

            result = client._upload_file(pdf, {})

        assert result == "fid-456"

    def test_success_with_nested_data_file_id(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": {"file_id": "nested-fid"}}
            mock_post.return_value = mock_resp

            result = client._upload_file(pdf, {})

        assert result == "nested-fid"

    def test_http_error(self, tmp_path):
        import requests as req
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = req.HTTPError("500 Server Error")
            mock_post.return_value = mock_resp

            with pytest.raises(req.HTTPError):
                client._upload_file(pdf, {})


class TestSubmitTask:
    def test_success_with_task_id(self):
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"task_id": "task-123"}
            mock_post.return_value = mock_resp

            result = client._submit_task("fid-1", {})

        assert result == "task-123"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert "json" in call_kwargs
        assert call_kwargs["json"]["file_id"] == "fid-1"

    def test_success_with_id_fallback(self):
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"id": "task-456"}
            mock_post.return_value = mock_resp

            result = client._submit_task("fid-1", {})

        assert result == "task-456"

    def test_success_with_nested_data_task_id(self):
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"data": {"task_id": "nested-task"}}
            mock_post.return_value = mock_resp

            result = client._submit_task("fid-1", {})

        assert result == "nested-task"

    def test_http_error(self):
        import requests as req
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = req.HTTPError("400 Bad Request")
            mock_post.return_value = mock_resp

            with pytest.raises(req.HTTPError):
                client._submit_task("fid-1", {})


class TestPollTask:
    def test_completed_immediately(self):
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "completed",
                "results": {"md_content": "# Hello", "content_list": []},
            }
            mock_get.return_value = mock_resp

            result = client._poll_task("task-1", {}, timeout=30, poll_interval=1)

        assert result == {"md_content": "# Hello", "content_list": []}
        assert mock_get.call_count == 1

    def test_completed_from_nested_data_results(self):
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "completed",
                "data": {"results": {"md_content": "# Nested", "content_list": []}},
            }
            mock_get.return_value = mock_resp

            result = client._poll_task("task-1", {}, timeout=30, poll_interval=1)

        assert result == {"md_content": "# Nested", "content_list": []}

    def test_completed_after_polling(self):
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.get") as mock_get:
            mock_get.side_effect = [
                MagicMock(json=MagicMock(return_value={"status": "processing"})),
                MagicMock(json=MagicMock(return_value={"status": "processing"})),
                MagicMock(json=MagicMock(return_value={
                    "status": "completed",
                    "results": {"md_content": "# Done"},
                })),
            ]

            with patch("peripatos_core.mineru_client.time.sleep") as mock_sleep:
                result = client._poll_task("task-1", {}, timeout=30, poll_interval=1)

        assert result == {"md_content": "# Done"}
        assert mock_get.call_count == 3
        assert mock_sleep.call_count == 2

    def test_failed_status(self):
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "failed",
                "error": "File corrupted",
            }
            mock_get.return_value = mock_resp

            with pytest.raises(RuntimeError, match="MinerU task failed: File corrupted"):
                client._poll_task("task-1", {}, timeout=30, poll_interval=1)

    def test_error_status(self):
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {
                "status": "error",
                "message": "Server overloaded",
            }
            mock_get.return_value = mock_resp

            with pytest.raises(RuntimeError, match="MinerU task failed: Server overloaded"):
                client._poll_task("task-1", {}, timeout=30, poll_interval=1)

    def test_failed_with_fallback_error_message(self):
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "failed"}
            mock_get.return_value = mock_resp

            with pytest.raises(RuntimeError, match="MinerU task failed: Unknown error"):
                client._poll_task("task-1", {}, timeout=30, poll_interval=1)

    def test_timeout(self):
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"status": "processing"}
            mock_get.return_value = mock_resp

            with patch("peripatos_core.mineru_client.time.sleep"):
                with patch("peripatos_core.mineru_client.time.time") as mock_time:
                    mock_time.side_effect = [100.0, 135.0]
                    with pytest.raises(TimeoutError, match="did not complete within"):
                        client._poll_task("task-1", {}, timeout=30, poll_interval=1)

    def test_http_error_during_poll(self):
        import requests as req
        client = MinerUClient()
        with patch("peripatos_core.mineru_client.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.raise_for_status.side_effect = req.HTTPError("503 Unavailable")
            mock_get.return_value = mock_resp

            with pytest.raises(req.HTTPError):
                client._poll_task("task-1", {}, timeout=30, poll_interval=1)


class TestExtract:
    def test_end_to_end_with_markdown(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient(token="test-token")

        with patch.object(client, "_upload_file", return_value="fid-1") as mock_upload, \
             patch.object(client, "_submit_task", return_value="task-1") as mock_submit, \
             patch.object(client, "_poll_task", return_value={
                 "md_content": "# Abstract\n\nHello world.\n\n## Methods\n\nMethods text.",
                 "content_list": [
                     {"text": "Abstract", "text_level": 1},
                     {"text": "Hello world.", "text_level": 0},
                     {"text": "Methods", "text_level": 2},
                     {"text": "Methods text.", "text_level": 0},
                 ],
             }) as mock_poll:

            result = client.extract(pdf)

        assert isinstance(result, MinerUResult)
        assert "Hello world" in result.markdown
        assert "Abstract" in result.sections
        assert "Methods" in result.sections
        mock_upload.assert_called_once()
        mock_submit.assert_called_once_with("fid-1", mock_upload.call_args[0][1])
        mock_poll.assert_called_once()

    def test_fallback_to_content_list_when_no_md_content(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()

        with patch.object(client, "_upload_file", return_value="fid-1"), \
             patch.object(client, "_submit_task", return_value="task-1"), \
             patch.object(client, "_poll_task", return_value={
                 "md_content": "",
                 "content_list": [
                     {"text": "Title", "text_level": 1},
                     {"text": "Body text here.", "text_level": 0},
                 ],
             }):

            result = client.extract(pdf)

        assert result.markdown == "# Title\n\nBody text here."
        assert result.sections == ["Title"]

    def test_default_timeout_and_poll_interval(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()

        with patch.object(client, "_upload_file", return_value="fid-1"), \
             patch.object(client, "_submit_task", return_value="task-1"), \
             patch.object(client, "_poll_task") as mock_poll:

            mock_poll.return_value = {"md_content": "# Test", "content_list": []}
            client.extract(pdf)

        mock_poll.assert_called_once_with("task-1", client._headers(), 300, 5)

    def test_custom_timeout_and_poll_interval(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()

        with patch.object(client, "_upload_file", return_value="fid-1"), \
             patch.object(client, "_submit_task", return_value="task-1"), \
             patch.object(client, "_poll_task") as mock_poll:

            mock_poll.return_value = {"md_content": "# Test", "content_list": []}
            client.extract(pdf, timeout=60, poll_interval=2)

        mock_poll.assert_called_once_with("task-1", client._headers(), 60, 2)

    def test_raises_on_upload_error(self, tmp_path):
        import requests as req
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()

        with patch.object(client, "_upload_file", side_effect=req.HTTPError("403")), \
             patch.object(client, "_submit_task") as mock_submit, \
             patch.object(client, "_poll_task") as mock_poll:

            with pytest.raises(req.HTTPError):
                client.extract(pdf)

        mock_submit.assert_not_called()
        mock_poll.assert_not_called()

    def test_raises_on_poll_runtime_error(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()

        with patch.object(client, "_upload_file", return_value="fid-1"), \
             patch.object(client, "_submit_task", return_value="task-1"), \
             patch.object(client, "_poll_task", side_effect=RuntimeError("MinerU task failed: bad file")):

            with pytest.raises(RuntimeError, match="MinerU task failed: bad file"):
                client.extract(pdf)

    def test_raises_on_poll_timeout(self, tmp_path):
        pdf = _make_sample_pdf(tmp_path)
        client = MinerUClient()

        with patch.object(client, "_upload_file", return_value="fid-1"), \
             patch.object(client, "_submit_task", return_value="task-1"), \
             patch.object(client, "_poll_task", side_effect=TimeoutError("did not complete")):

            with pytest.raises(TimeoutError, match="did not complete"):
                client.extract(pdf)


class TestContentListToMarkdown:
    def test_headings_level_1(self):
        content_list = [
            {"text": "Introduction", "text_level": 1},
        ]
        result = MinerUClient._content_list_to_markdown(content_list)
        assert result == "# Introduction"

    def test_headings_level_2_and_3(self):
        content_list = [
            {"text": "Chapter 1", "text_level": 2},
            {"text": "Section 1.1", "text_level": 3},
        ]
        result = MinerUClient._content_list_to_markdown(content_list)
        assert result == "## Chapter 1\n\n### Section 1.1"

    def test_plain_text_level_0(self):
        content_list = [
            {"text": "Just some paragraph text.", "text_level": 0},
        ]
        result = MinerUClient._content_list_to_markdown(content_list)
        assert result == "Just some paragraph text."

    def test_empty_text_items(self):
        content_list = [
            {"text": "", "text_level": 0},
            {"text": "Real heading", "text_level": 1},
            {"text": "Visible text", "text_level": 0},
        ]
        result = MinerUClient._content_list_to_markdown(content_list)
        assert result == "# Real heading\n\nVisible text"

    def test_missing_text_level_defaults_to_0(self):
        content_list = [
            {"text": "Plain paragraph"},
        ]
        result = MinerUClient._content_list_to_markdown(content_list)
        assert result == "Plain paragraph"

    def test_mixed_content(self):
        content_list = [
            {"text": "Abstract", "text_level": 1},
            {"text": "This is the abstract.", "text_level": 0},
            {"text": "Introduction", "text_level": 2},
            {"text": "Welcome to the paper.", "text_level": 0},
        ]
        result = MinerUClient._content_list_to_markdown(content_list)
        expected = "# Abstract\n\nThis is the abstract.\n\n## Introduction\n\nWelcome to the paper."
        assert result == expected

    def test_empty_content_list(self):
        result = MinerUClient._content_list_to_markdown([])
        assert result == ""

    def test_only_headings(self):
        content_list = [
            {"text": "A", "text_level": 1},
            {"text": "B", "text_level": 1},
            {"text": "C", "text_level": 2},
        ]
        result = MinerUClient._content_list_to_markdown(content_list)
        assert result == "# A\n\n# B\n\n## C"


class TestExtractSections:
    def test_from_content_list_with_headings(self):
        content_list = [
            {"text": "Intro", "text_level": 1},
            {"text": "Body text", "text_level": 0},
            {"text": "Methods", "text_level": 2},
        ]
        result = MinerUClient._extract_sections("# Ignored\n\nBody text\n\n## Methods", content_list)
        assert result == ["Intro", "Methods"]

    def test_from_content_list_only_level_greater_than_0(self):
        content_list = [
            {"text": "Heading Only", "text_level": 1},
            {"text": "No heading here", "text_level": 0},
            {"text": "Another Heading", "text_level": 3},
        ]
        result = MinerUClient._extract_sections("", content_list)
        assert result == ["Heading Only", "Another Heading"]

    def test_fallback_to_markdown_when_no_headings_in_content_list(self):
        content_list = [
            {"text": "Plain text", "text_level": 0},
            {"text": "More plain text", "text_level": 0},
        ]
        markdown = "# Introduction\n\nBody.\n\n## Methods\n\nMore body.\n\n### Details\n\nExtra."
        result = MinerUClient._extract_sections(markdown, content_list)
        assert result == ["Introduction", "Methods", "Details"]

    def test_fallback_to_markdown_when_content_list_empty(self):
        markdown = "# Abstract\n\nText.\n\n## Results\n\nData."
        result = MinerUClient._extract_sections(markdown, [])
        assert result == ["Abstract", "Results"]

    def test_fallback_strips_leading_pound_signs(self):
        markdown = "#  Leading space  \n###  Triple hash  "
        result = MinerUClient._extract_sections(markdown, [])
        assert result == ["Leading space", "Triple hash"]

    def test_empty_markdown_and_no_headings_in_content_list(self):
        result = MinerUClient._extract_sections("", [{"text": "Plain", "text_level": 0}])
        assert result == []

    def test_empty_markdown_and_empty_content_list(self):
        result = MinerUClient._extract_sections("", [])
        assert result == []

    def test_markdown_with_no_headings(self):
        result = MinerUClient._extract_sections("Just plain text.\nNo headings here.", [])
        assert result == []
