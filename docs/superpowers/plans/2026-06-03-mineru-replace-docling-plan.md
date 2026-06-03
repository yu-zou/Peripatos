# Replace Docling with MinerU Cloud API — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace docling (~570MB ML deps) with MinerU cloud API as the PDF parser, with PyMuPDF as a lightweight internal fallback.

**Architecture:** `PDFParser` first tries MinerU cloud API (HTTP to `mineru.net`), falling back to PyMuPDF on any failure. Config field `parser.mineru_token` enables Precision extract mode.

**Tech Stack:** stdlib `httpx`/`requests`, `pymupdf` (new dep), `pydantic` (not needed — plain dataclasses).

---

### Task 1: Add ParserConfig to config module

**Files:**
- Modify: `peripatos_core/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Add ParserConfig dataclass and KNOWN_PARSER_KEYS**

In `peripatos_core/config.py`, after `KNOWN_DEFAULTS_KEYS` (line 26), add:

```python
KNOWN_PARSER_KEYS = {"mineru_token"}
```

After the `Defaults` dataclass (line 80), add:

```python
@dataclass
class ParserConfig:
    mineru_token: str = ""
```

- [ ] **Step 2: Wire ParserConfig into Settings and _apply_overrides**

Add a field to `Settings` (after the `rag` field, line 119):

```python
    parser: ParserConfig = field(default_factory=ParserConfig)
```

In `_apply_overrides()`, add handling for the `"parser"` section (after the `"defaults"` block, around line 176):

```python
    if "parser" in data:
        parser_data = data["parser"]
        _warn_unknown("parser", parser_data, KNOWN_PARSER_KEYS)
        for k in KNOWN_PARSER_KEYS:
            if k in parser_data:
                setattr(settings.parser, k, parser_data[k])
```

- [ ] **Step 3: Add `"parser"` to KNOWN_KEYS**

Change line 21 from:
```python
KNOWN_KEYS = {"$schema", "llm", "tts", "defaults", "rag"}
```
to:
```python
KNOWN_KEYS = {"$schema", "llm", "tts", "defaults", "rag", "parser"}
```

- [ ] **Step 4: Write the tests**

Add to `tests/test_config.py`:

```python
# ── Parser config ──────────────────────────────────────────────

def test_parser_config_defaults():
    from peripatos_core.config import ParserConfig
    cfg = ParserConfig()
    assert cfg.mineru_token == ""


def test_parser_token_loaded_from_config(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"parser": {"mineru_token": "test-token-123"}}))
    settings = load_settings(config_path=cfg)
    assert settings.parser.mineru_token == "test-token-123"


def test_parser_unknown_key_warns(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"parser": {"unknown_field": "value"}}))
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        load_settings(config_path=cfg)
    assert any("unknown_field" in str(warning.message) for warning in w)
```

- [ ] **Step 5: Run the tests**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && pytest tests/test_config.py::test_parser_config_defaults tests/test_config.py::test_parser_token_loaded_from_config tests/test_config.py::test_parser_unknown_key_warns -v
```

Expected: 3 PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && git add peripatos_core/config.py tests/test_config.py && git commit -m "feat: add ParserConfig with mineru_token field"
```

---

### Task 2: Rewrite PDFParser with MinerU API + PyMuPDF fallback

**Files:**
- Modify: `peripatos_core/parser.py` (complete rewrite)
- Modify: `tests/test_parser.py` (rewrite tests)
- Create: `peripatos_core/mineru_client.py`

- [ ] **Step 1: Create the MinerU cloud client**

Create `peripatos_core/mineru_client.py`:

```python
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
    1. Upload file → get file_id
    2. Submit extract task → get task_id
    3. Poll task status → completed
    4. Fetch results → markdown + content_list
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

        # Step 1: Upload file
        file_id = self._upload_file(pdf_path, headers)

        # Step 2: Submit extract task
        task_id = self._submit_task(file_id, headers)

        # Step 3: Poll for completion
        results = self._poll_task(task_id, headers, timeout, poll_interval)

        # Step 4: Parse results
        markdown = results.get("md_content", "")
        content_list = results.get("content_list", [])

        if not markdown and content_list:
            markdown = self._content_list_to_markdown(content_list)

        sections = self._extract_sections(markdown, content_list)
        return MinerUResult(markdown=markdown, sections=sections)

    def _headers(self) -> dict[str, str]:
        """Return HTTP headers with auth if token is set."""
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _upload_file(self, pdf_path: Path, headers: dict[str, str]) -> str:
        """Upload PDF and return file_id."""
        with open(pdf_path, "rb") as f:
            resp = requests.post(
                f"{_MINERU_API_BASE}/file-urls",
                headers=headers,
                files={"file": (pdf_path.name, f, "application/pdf")},
                timeout=60,
            )
        resp.raise_for_status()
        data = resp.json()
        # The response structure may vary — adapt based on actual API
        return data.get("file_id") or data.get("id") or data.get("data", {}).get("file_id")

    def _submit_task(self, file_id: str, headers: dict[str, str]) -> str:
        """Submit extract task and return task_id."""
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
        """Poll task status until completed or timeout."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(poll_interval)
            resp = requests.get(
                f"{_MINERU_API_BASE}/extract/task/{task_id}",
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status", "")

            if status == "completed":
                # Results may be in data["results"] or data["data"]["results"]
                return data.get("results") or data.get("data", {}).get("results", {})
            elif status in ("failed", "error"):
                error = data.get("error", data.get("message", "Unknown error"))
                raise RuntimeError(f"MinerU task failed: {error}")
            # else: still processing (status may be "processing", "queued", etc.)

        raise TimeoutError(f"MinerU task did not complete within {timeout}s")

    @staticmethod
    def _content_list_to_markdown(content_list: list[dict]) -> str:
        """Convert MinerU content_list to markdown."""
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
        """Extract section headings from content_list or fallback to regex."""
        if content_list:
            sections = [
                item["text"] for item in content_list
                if item.get("text_level", 0) > 0
            ]
            if sections:
                return sections

        # Fallback: regex from markdown
        return [
            line.lstrip("#").strip()
            for line in markdown.splitlines()
            if line.startswith("#")
        ]
```

> **Note:** The exact MinerU cloud API response shapes (file_id field name, results nesting) may differ slightly from the plan. The implementer should verify against `https://mineru.net/apiManage/docs` or the `mineru-open-sdk` source code and adjust field names accordingly. The overall workflow (upload → submit → poll → results) is confirmed.

- [ ] **Step 2: Rewrite PDFParser to use MinerU + PyMuPDF fallback**

Replace the entire contents of `peripatos_core/parser.py`:

```python
"""PDF parser wrapping MinerU cloud API with PyMuPDF fallback."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from peripatos_core.exceptions import ParseError
from peripatos_core.mineru_client import MinerUClient, MinerUResult

logger = logging.getLogger(__name__)


@dataclass
class ParsedPaper:
    """Result of parsing a PDF."""
    markdown: str
    sections: list[str] = field(default_factory=list)
    full_text: str = ""


class PDFParser:
    """Parses a PDF using MinerU cloud API, falling back to PyMuPDF.

    MinerU requires network access and provides high-quality extraction
    (tables, formulas, headings). On any failure, PyMuPDF is used as
    a lightweight fallback (text-only, no ML).
    """

    def __init__(self, mineru_token: str | None = None) -> None:
        self._mineru_token = mineru_token if mineru_token else None

    def parse(self, pdf_path: Path) -> ParsedPaper:
        """Parse a PDF and return structured content.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            ParsedPaper with markdown text and section headings.
        """
        if not pdf_path.exists():
            raise ParseError(f"PDF not found: {pdf_path}")
        if pdf_path.suffix.lower() != ".pdf":
            raise ParseError(f"Expected .pdf file, got: {pdf_path.suffix}")

        # Step 1: Try MinerU cloud API
        try:
            client = MinerUClient(token=self._mineru_token)
            result = client.extract(pdf_path)
            return ParsedPaper(
                markdown=result.markdown,
                sections=result.sections,
                full_text=result.markdown,
            )
        except Exception as exc:
            logger.warning(
                "MinerU API unavailable (%s), falling back to PyMuPDF. "
                "Tables and formulas will not be extracted.",
                exc,
            )

        # Step 2: PyMuPDF fallback
        return self._parse_with_pymupdf(pdf_path)

    @staticmethod
    def _parse_with_pymupdf(pdf_path: Path) -> ParsedPaper:
        """Parse PDF using PyMuPDF (lightweight, text-only)."""
        try:
            import pymupdf  # type: ignore[reportMissingImports]
        except ImportError as exc:
            raise ParseError("PyMuPDF is not installed") from exc

        try:
            doc = pymupdf.open(str(pdf_path))
            markdown_parts = []
            sections = []
            for page in doc:
                text = page.get_text()
                markdown_parts.append(text)
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped and (stripped.isupper() or stripped.startswith("#")):
                        sections.append(stripped.lstrip("#").strip())
            doc.close()

            markdown = "\n\n".join(markdown_parts)
            return ParsedPaper(
                markdown=markdown,
                sections=sections,
                full_text=markdown,
            )
        except Exception as exc:
            raise ParseError(f"PyMuPDF failed to parse {pdf_path}: {exc}") from exc
```

- [ ] **Step 3: Rewrite parser tests**

Replace `tests/test_parser.py`:

```python
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


# ── MinerU API tests ──────────────────────────────────────────

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
        from concurrent.futures import TimeoutError
        mock_extract.side_effect = TimeoutError("timed out")
        result = parser.parse(pdf)

    assert isinstance(result, ParsedPaper)


def test_mineru_no_token_uses_flash_mode(tmp_path):
    """Without token, MinerU uses flash extract mode."""
    parser = PDFParser()  # no token
    pdf = _make_sample_pdf(tmp_path)

    with patch("peripatos_core.mineru_client.MinerUClient") as MockClient:
        mock_instance = MagicMock()
        mock_instance.extract.return_value = MagicMock(
            markdown="Flash result",
            sections=[],
        )
        MockClient.return_value = mock_instance
        MockClient.assert_called_once_with(token=None)

        result = parser.parse(pdf)
        assert result.markdown == "Flash result"


# ── PyMuPDF fallback tests ────────────────────────────────────

def test_pymupdf_fallback_extracts_text(tmp_path):
    """When MinerU fails, PyMuPDF extracts text."""
    parser = PDFParser()
    pdf = _make_sample_pdf(tmp_path)

    with patch("peripatos_core.mineru_client.MinerUClient.extract") as mock_extract:
        mock_extract.side_effect = RuntimeError("API down")
        result = parser.parse(pdf)

    assert isinstance(result, ParsedPaper)
    assert len(result.markdown) > 0


def test_both_fail_raises_parse_error(tmp_path, monkeypatch):
    """When both MinerU and PyMuPDF fail, ParseError is raised."""
    parser = PDFParser()
    pdf = _make_sample_pdf(tmp_path)

    with patch("peripatos_core.mineru_client.MinerUClient.extract") as mock_mineru:
        mock_mineru.side_effect = RuntimeError("API down")

        # Make pymupdf import fail
        with pytest.raises(ParseError, match="PyMuPDF is not installed|PyMuPDF failed"):
            with patch.dict("sys.modules", {"pymupdf": None}):
                parser.parse(pdf)


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


# ── Section extraction tests ──────────────────────────────────

def test_mineru_extracts_sections_from_content_list(tmp_path):
    """MinerU result with content_list produces sections."""
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
```

- [ ] **Step 4: Install pymupdf**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && pip install pymupdf
```

- [ ] **Step 5: Run the parser tests**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && pytest tests/test_parser.py -v
```

Expected: All PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && git add peripatos_core/mineru_client.py peripatos_core/parser.py tests/test_parser.py && git commit -m "feat: rewrite PDFParser with MinerU API + PyMuPDF fallback"
```

---

### Task 3: Wire parser config into CLI

**Files:**
- Modify: `peripatos_core/cli.py`

- [ ] **Step 1: Pass mineru_token to PDFParser**

In `cmd_generate()`, find the line that creates `PDFParser` (line 39):
```python
    parser = PDFParser()
```

Replace with:
```python
    parser = PDFParser(mineru_token=settings.parser.mineru_token or None)
```

- [ ] **Step 2: Commit**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && git add peripatos_core/cli.py && git commit -m "feat: wire mineru_token from config to PDFParser"
```

---

### Task 4: Update config schema and pyproject.toml

**Files:**
- Modify: `schema/config.schema.json`
- Modify: `pyproject.toml`

- [ ] **Step 1: Add "parser" section to JSON schema**

In `schema/config.schema.json`, add after the `"rag"` section (before the closing `}` of `properties`):

```json
    ,
    "parser": {
      "type": "object",
      "description": "PDF parser configuration.",
      "additionalProperties": false,
      "properties": {
        "mineru_token": {
          "type": "string",
          "default": "",
          "description": "MinerU cloud API token from mineru.net/apiManage/token. Enables Precision extract mode (≤600 pages). Leave empty for Flash extract (≤20 pages)."
        }
      }
    }
```

- [ ] **Step 2: Update pyproject.toml dependencies**

Change `pyproject.toml` dependencies from:
```toml
dependencies = [
    "typer>=0.12,<1.0",
    "pydub>=0.25,<1.0",
    "audioop-lts>=0.2.1; python_version >= \"3.13\"",
    "mutagen>=1.47,<2.0",
    "openai>=1.40,<2.0",
    "edge-tts>=7.2,<8.0",
    "docling>=2.0",
    "requests>=2.31,<3.0",
    "pyyaml>=6.0,<7.0",
    "json-repair>=0.30,<1.0",
    "faiss-cpu>=1.8.0",
    "numpy>=1.26.0",
    "beautifulsoup4>=4.12.0",
    "sentence-transformers>=3.0",
]
```

to:

```toml
dependencies = [
    "typer>=0.12,<1.0",
    "pydub>=0.25,<1.0",
    "audioop-lts>=0.2.1; python_version >= \"3.13\"",
    "mutagen>=1.47,<2.0",
    "openai>=1.40,<2.0",
    "edge-tts>=7.2,<8.0",
    "requests>=2.31,<3.0",
    "pyyaml>=6.0,<7.0",
    "json-repair>=0.30,<1.0",
    "faiss-cpu>=1.8.0",
    "numpy>=1.26.0",
    "beautifulsoup4>=4.12.0",
    "pymupdf>=1.24.0",
]
```

- [ ] **Step 3: Remove docling and sentence-transformers**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && pip uninstall -y docling docling-core docling-ibm-models docling-parse sentence-transformers
```

- [ ] **Step 4: Run the full test suite**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && pytest tests/ --ignore=tests/test_e2e.py --ignore=tests/test_http_retry.py -m "not integration" --tb=short
```

Expected: All tests pass (should be ~176+ tests, minus the integration test which will be skipped).

- [ ] **Step 5: Commit**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && git add schema/config.schema.json pyproject.toml && git commit -m "deps: replace docling+sentence-transformers with pymupdf, add parser schema"
```

---

### Task 5: Final verification and cleanup

**Files:**
- Verify: `peripatos_core/rag/sources.py` (uses PDFParser)

- [ ] **Step 1: Check rag/sources.py compatibility**

Read `peripatos_core/rag/sources.py` line 15. It imports `PDFParser` — verify the import still works (it does, we kept the same class name and interface). No changes needed.

- [ ] **Step 2: Verify no remaining docling references**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && grep -r "docling" peripatos_core/ --include="*.py"
```

Expected: No matches.

- [ ] **Step 3: Verify no remaining sentence-transformers references in required code**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && grep -r "sentence_transformers\|SentenceTransformer" peripatos_core/ --include="*.py"
```

Expected: Only in `peripatos_core/rag/embedder.py` inside a try/except block (already guarded).

- [ ] **Step 4: Final full test suite run**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && pytest tests/ --ignore=tests/test_e2e.py --ignore=tests/test_http_retry.py -m "not integration" --tb=short
```

Expected: All PASS.

- [ ] **Step 5: Final commit**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && git status && git add -A && git commit -m "chore: verify clean migration from docling to MinerU"
```
