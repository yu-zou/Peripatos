"""MinerU cloud API client for PDF parsing."""
from __future__ import annotations

import io
import json
import logging
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_FLASH_API_BASE = "https://mineru.net/api/v1/agent"
_PRECISION_API_BASE = "https://mineru.net/api/v4"


@dataclass
class MinerUResult:
    markdown: str
    sections: list[str]


class MinerUClient:
    """HTTP client for the MinerU cloud API (mineru.net).

    Two modes:
    - Flash Extract: no auth, <=10MB/20 pages, uses /api/v1/agent/
    - Precision Extract: auth required, <=200MB/200 pages, uses /api/v4/
    """

    def __init__(self, token: str | None = None) -> None:
        self._token = token

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    @staticmethod
    def _check_api_error(data: dict) -> None:
        if data.get("code") != 0:
            raise RuntimeError(f"MinerU API error: {data.get('msg', 'Unknown error')}")

    def extract(self, pdf_path: Path, timeout: int = 300, poll_interval: int = 5) -> MinerUResult:
        """Precision Extract — auth required, full features (tables, formulas).

        Submit a local PDF to MinerU cloud API and return parsed result.

        Args:
            pdf_path: Path to the PDF file.
            timeout: Maximum seconds to wait for the result.
            poll_interval: Seconds between polling attempts.

        Returns:
            MinerUResult with markdown and extracted sections.

        Raises:
            RuntimeError, TimeoutError on failure.
        """
        if not self._token:
            raise RuntimeError("Precision Extract requires an API token")

        headers = self._headers()

        resp = requests.post(
            f"{_PRECISION_API_BASE}/file-urls/batch",
            headers=headers,
            json={"files": [{"name": pdf_path.name}], "model_version": "vlm"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        self._check_api_error(data)

        batch_data = data.get("data", {})
        batch_id = batch_data.get("batch_id")
        file_urls = batch_data.get("file_urls", [])

        if not file_urls:
            raise RuntimeError("No upload URL returned from batch file-urls endpoint")

        self._upload_file_to_url(file_urls[0], pdf_path)

        result_data = self._poll_batch(batch_id, headers, timeout, poll_interval)

        full_zip_url = result_data.get("full_zip_url")
        if not full_zip_url:
            raise RuntimeError("No full_zip_url in batch result")

        markdown, content_list = self._download_and_extract_zip(full_zip_url, headers)

        sections = self._extract_sections_from_markdown(markdown, content_list)
        return MinerUResult(markdown=markdown, sections=sections)

    def flash_extract(self, pdf_path: Path, timeout: int = 300,
                      poll_interval: int = 5) -> MinerUResult:
        """Flash Extract — no auth needed, fast, <=10MB/20 pages.

        Uploads the file via the agent parse flow (init -> upload -> poll -> download).
        No API token required.

        Args:
            pdf_path: Path to the PDF file.
            timeout: Maximum seconds to wait for the result.
            poll_interval: Seconds between polling attempts.

        Returns:
            MinerUResult with markdown and extracted sections.

        Raises:
            RuntimeError, TimeoutError on failure.
        """
        resp = requests.post(
            f"{_FLASH_API_BASE}/parse/file",
            json={"file_name": pdf_path.name},
            headers={"Accept": "application/json"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        self._check_api_error(data)

        task_data = data.get("data", {})
        task_id = task_data.get("task_id")
        file_url = task_data.get("file_url")

        if not file_url:
            raise RuntimeError("No upload URL returned from parse/file endpoint")

        self._upload_file_to_url(file_url, pdf_path)

        markdown_url = self._poll_flash_task(task_id, timeout, poll_interval)

        markdown = self._download_markdown(markdown_url)

        sections = self._extract_sections_from_markdown(markdown, [])
        return MinerUResult(markdown=markdown, sections=sections)

    @staticmethod
    def _upload_file_to_url(upload_url: str, pdf_path: Path) -> None:
        with open(pdf_path, "rb") as f:
            resp = requests.put(upload_url, data=f.read(), timeout=120)
        resp.raise_for_status()

    def _poll_batch(self, batch_id: str, headers: dict[str, str],
                    timeout: int, poll_interval: int) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = requests.get(
                f"{_PRECISION_API_BASE}/extract-results/batch/{batch_id}",
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            self._check_api_error(data)

            batch_data = data.get("data", {})
            extract_results = batch_data.get("extract_result", [])

            if extract_results:
                result = extract_results[0]
                state = result.get("state", "")

                if state == "done":
                    return result
                elif state == "failed":
                    error = result.get("err_msg", batch_data.get("err_msg", "Unknown error"))
                    raise RuntimeError(f"MinerU Precision task failed: {error}")

            time.sleep(poll_interval)

        raise TimeoutError(f"MinerU Precision task did not complete within {timeout}s")

    def _poll_flash_task(self, task_id: str, timeout: int,
                         poll_interval: int) -> str:
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = requests.get(
                f"{_FLASH_API_BASE}/parse/{task_id}",
                headers={"Accept": "application/json"},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            self._check_api_error(data)

            task_data = data.get("data", {})
            state = task_data.get("state", "")

            if state == "done":
                markdown_url = task_data.get("markdown_url")
                if not markdown_url:
                    raise RuntimeError("Task completed but no markdown_url returned")
                return markdown_url
            elif state == "failed":
                error = task_data.get("err_msg", "Unknown error")
                raise RuntimeError(f"MinerU Flash task failed: {error}")

            time.sleep(poll_interval)

        raise TimeoutError(f"MinerU Flash task did not complete within {timeout}s")

    @staticmethod
    def _download_markdown(url: str) -> str:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def _download_and_extract_zip(zip_url: str, headers: dict[str, str]) -> tuple[str, list]:
        resp = requests.get(zip_url, headers=headers, timeout=120)
        resp.raise_for_status()

        markdown = ""
        content_list = []

        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            if "full.md" in zf.namelist():
                markdown = zf.read("full.md").decode("utf-8")
            if "content_list.json" in zf.namelist():
                content_list = json.loads(zf.read("content_list.json").decode("utf-8"))

        return markdown, content_list

    @staticmethod
    def _extract_sections_from_markdown(markdown: str, content_list: list) -> list[str]:
        if content_list:
            sections = [
                item["text"] for item in content_list
                if item.get("text_level", 0) > 0
            ]
            if sections:
                return sections

        return [
            line.lstrip("#").strip()
            for line in markdown.splitlines()
            if line.startswith("#")
        ]
