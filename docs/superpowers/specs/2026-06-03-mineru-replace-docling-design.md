# Replace Docling with MinerU Cloud API — Design Spec

## Goal

Replace docling (PDF parser pulling ~570MB of ML dependencies: torch, transformers, onnxruntime) with MinerU's cloud API (`mineru.net`) as the primary PDF parser. PyMuPDF becomes the lightweight internal fallback (~20MB).

## Current State

- Milestone tagged: `v1.3.0-docling` on HEAD
- `peripatos_core/parser.py`: `PDFParser` wraps docling's `DocumentConverter` in-process
- `tests/test_parser.py`: 6 tests, including 1 integration test requiring `RUN_INTEGRATION=1`
- `pyproject.toml`: `docling` listed as required dependency
- `pyproject.toml`: `sentence-transformers` also listed as required but not installed locally

## Architecture

### Provider Flow

```
PDFParser.parse()
├── Step 1: Try MinerU cloud API
│   ├── If mineru_token set → Precision extract (≤600 pages, ≤200MB)
│   ├── If no token → Flash extract (≤20 pages, ≤10MB)
│   └── On success → return ParsedPaper(markdown, sections, full_text)
│
├── Step 2: On ANY failure (network, rate limit, 401, 500, timeout)
│   ├── Log warning: "MinerU API unavailable, falling back to PyMuPDF"
│   └── Fall through to Step 3
│
└── Step 3: PyMuPDF fallback
    ├── Extract text via pymupdf
    ├── Generate markdown from text blocks (regex headings)
    └── On failure → hard ParseError
```

### Config Schema

```json
{
  "parser": {
    "mineru_token": "your-token-here"
  }
}
```

- No `provider` field — MinerU is the only external backend
- Token lookup: config `parser.mineru_token` → `None`
- Token not set → Flash extract mode (no auth required)
- Token set → Precision extract (auth required, higher limits)

### Dependencies

| Action | Package | Reason |
|--------|---------|--------|
| **Add** | `pymupdf` (required) | Lightweight PDF extraction fallback (~20MB) |
| **Remove** | `docling` | ~570MB ML deps replaced by HTTP API |
| **Remove** | `sentence-transformers` | Only needed for local embeddings, should be optional |

Net effect: base install drops from ~2GB to ~300MB. Package count: ~212→~130.

## Implementation Details

### MinerU Cloud Client

- Use `mineru-open-sdk` Python package (pip: `mineru-open-sdk`)
- OR use direct HTTP with `requests` (lighter, avoids another dependency)
- Base URL: `https://mineru.net/api/v4`
- Auth: `Authorization: Bearer <token>` header
- Endpoint: `POST /extract/task` (submit), `GET /extract/task/{task_id}` (poll)
- Timeout: 300 seconds max
- Response: markdown via `md_content` field

### PyMuPDF Fallback

```python
import pymupdf

doc = pymupdf.open(str(pdf_path))
markdown_parts = []
sections = []
for page in doc:
    text = page.get_text()
    markdown_parts.append(text)
    for line in text.splitlines():
        if line.isupper() or line.startswith("#"):
            sections.append(line.lstrip("#").strip())
markdown = "\n\n".join(markdown_parts)
```

### Error Messages

- MinerU failure + PyMuPDF fallback: `WARNING: MinerU API unavailable (rate limit / network error), falling back to PyMuPDF. Tables and formulas will not be extracted.`
- Both fail: `ParseError: All PDF parsers failed. Check network connection or set parser.mineru_token in config.`

## Tests

- Unit test: MinerU success (mocked HTTP)
- Unit test: MinerU failure → PyMuPDF fallback (mocked HTTP + real pymupdf)
- Unit test: Config token resolution (present/absent)
- Unit test: PyMuPDF fallback alone (mineru disabled)
- Unit test: Both fail → ParseError
- Existing integration test: update to skip if no `mineru_token` set in config
