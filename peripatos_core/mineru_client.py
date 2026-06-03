"""MinerU cloud API client for PDF parsing."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

_MINERU_API_BASE = "https://mineru.net/api/v4"


@dataclass
class MinerUResult:
    markdown: str
    sections: list[str]


class MinerUClient:
    """HTTP client for the MinerU cloud API (mineru.net).

    Workflow:
    1. Upload file -> get file_id
    2. Submit extract task -> get task_id
    3. Poll task status -> completed
    4. Fetch results -> markdown + content_list
    """

    def __init__(self, token: str | None = None) -> None:
        self._token = token

    def extract(self, pdf_path: Path, timeout: int = 300, poll_interval: int = 5) -> MinerUResult:
        """Submit a local PDF to MinerU cloud API and return parsed result.

        Args:
            pdf_path: Path to the PDF file.
            timeout: Maximum seconds to wait for the result.
            poll_interval: Seconds between polling attempts.

        Returns:
            MinerUResult with markdown and extracted sections.

        Raises:
            requests.HTTPError, RuntimeError, TimeoutError on failure.
        """
        headers = self._headers()

        file_id = self._upload_file(pdf_path, headers)

        task_id = self._submit_task(file_id, headers)

        results = self._poll_task(task_id, headers, timeout, poll_interval)

        markdown = results.get("md_content", "")
        content_list = results.get("content_list", [])

        if not markdown and content_list:
            markdown = self._content_list_to_markdown(content_list)

        sections = self._extract_sections(markdown, content_list)
        return MinerUResult(markdown=markdown, sections=sections)

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _upload_file(self, pdf_path: Path, headers: dict[str, str]) -> str:
        with open(pdf_path, "rb") as f:
            resp = requests.post(
                f"{_MINERU_API_BASE}/file-urls",
                headers=headers,
                files={"file": (pdf_path.name, f, "application/pdf")},
                timeout=60,
            )
        resp.raise_for_status()
        data = resp.json()
        return data.get("file_id") or data.get("id") or data.get("data", {}).get("file_id")

    def _submit_task(self, file_id: str, headers: dict[str, str]) -> str:
        resp = requests.post(
            f"{_MINERU_API_BASE}/extract/task",
            headers=headers,
            json={
                "file_id": file_id,
                "model_version": "pipeline",
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["task_id"]

    def _poll_task(self, task_id: str, headers: dict[str, str],
                   timeout: int, poll_interval: int) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = requests.get(
                f"{_MINERU_API_BASE}/extract/task/{task_id}",
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status", "")

            if status == "completed":
                return data.get("results") or data.get("data", {}).get("results", {})
            elif status in ("failed", "error"):
                error = data.get("error", data.get("message", "Unknown error"))
                raise RuntimeError(f"MinerU task failed: {error}")

            time.sleep(poll_interval)

        raise TimeoutError(f"MinerU task did not complete within {timeout}s")

    @staticmethod
    def _content_list_to_markdown(content_list: list[dict]) -> str:
        parts = []
        for item in content_list:
            text = item.get("text", "")
            level = item.get("text_level", 0)
            if level > 0:
                parts.append(f"{'#' * level} {text}")
            elif text:
                parts.append(text)
        return "\n\n".join(parts)

    @staticmethod
    def _extract_sections(markdown: str, content_list: list[dict]) -> list[str]:
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
