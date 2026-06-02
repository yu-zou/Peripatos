# Dual-Mode Embedder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable `rag.embedding_model` to use either a local `sentence-transformers` model or a remote OpenAI-compatible API, controlled by a new `rag.provider` config key.

**Architecture:** Add `rag.provider` field to `RAGConfig`. Pass it through to `Embedder` constructor. `Embedder` branches on provider value — local mode uses `sentence-transformers`, remote mode uses current HTTP behavior. Backward compatible with default `"openai_compatible"`.

**Tech Stack:** sentence-transformers, numpy, existing pydantic-free dataclasses.

---

### Task 1: Add `rag.provider` config field

**Files:**
- Modify: `peripatos_core/config.py`

- [ ] **Step 1: Add provider field and config key**

Read `peripatos_core/config.py`. Find `KNOWN_RAG_KEYS` and `RAGConfig`, then add `provider`:

```python
# Update KNOWN_RAG_KEYS to include "provider"
KNOWN_RAG_KEYS = {"embedding_model", "chunk_size", "chunk_overlap", "top_k", "cache_dir", "provider"}

# Update RAGConfig dataclass
@dataclass
class RAGConfig:
    provider: str = "openai_compatible"
    embedding_model: str = "openai/text-embedding-3-small"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5
    cache_dir: str | None = None
```

- [ ] **Step 2: Update `_apply_overrides` to handle provider**

The `_apply_overrides` function already loops over `KNOWN_RAG_KEYS` for the `rag` section. Verify the existing loop handles `provider` naturally since it's in `KNOWN_RAG_KEYS`. The existing code is:

```python
if "rag" in data:
    rag_data = data["rag"]
    _warn_unknown("rag", rag_data, KNOWN_RAG_KEYS)
    for k in KNOWN_RAG_KEYS:
        if k in rag_data:
            setattr(settings.rag, k, rag_data[k])
```

This already works — no code change needed in `_apply_overrides`, just the key set update.

- [ ] **Step 3: Verify import works**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && python -c "from peripatos_core.config import Settings, RAGConfig; s = Settings(); print(s.rag.provider)"
```

Expected: `openai_compatible`

- [ ] **Step 4: Commit**

```bash
git add peripatos_core/config.py
git commit -m "feat: add rag.provider config field (default: openai_compatible)"
```

---

### Task 2: Add sentence-transformers dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add sentence-transformers to dependencies**

Add `"sentence-transformers>=3.0"` to the `dependencies` list in `pyproject.toml`:

```toml
[project]
name = "peripatos-core"
version = "1.2.0"
description = "Convert academic papers to Socratic-dialogue podcasts"
requires-python = ">=3.10"
license = {text = "MIT"}
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

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "deps: add sentence-transformers for local embeddings"
```

---

### Task 3: Write tests for Embedder config and dual-mode behavior

**Files:**
- Create: `tests/test_embedder.py`

- [ ] **Step 1: Write tests**

```python
"""Tests for dual-mode Embedder (local vs remote)."""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np
from peripatos_core.rag.embedder import Embedder
from peripatos_core.exceptions import EmbeddingError


class TestRemoteEmbedder:
    """Remote (OpenAI-compatible) embedder tests."""

    @patch("peripatos_core.rag.embedder.request_with_retry")
    def test_remote_embedder_calls_api(self, mock_request):
        """Remote embedder POSTs to /embeddings endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 128} for _ in range(2)]
        }
        mock_request.return_value = mock_response

        embedder = Embedder(
            base_url="https://api.example.com",
            api_key="test-key",
            model="openai/text-embedding-3-small",
            provider="openai_compatible",
        )
        result = embedder.embed(["hello", "world"])

        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args.kwargs
        assert call_kwargs["url"] == "https://api.example.com/embeddings"
        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 128)

    def test_remote_embedder_is_default(self):
        """Default provider is openai_compatible (backward compat)."""
        embedder = Embedder(
            base_url="https://api.example.com",
            api_key="test-key",
            model="openai/text-embedding-3-small",
        )
        assert embedder._provider == "openai_compatible"


class TestLocalEmbedder:
    """Local (sentence-transformers) embedder tests."""

    @patch("peripatos_core.rag.embedder.SentenceTransformer")
    def test_local_embedder_calls_encode(self, mock_st):
        """Local embedder calls SentenceTransformer.encode()."""
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1] * 768, [0.2] * 768], dtype=np.float32)
        mock_st.return_value = mock_model

        embedder = Embedder(
            base_url="",
            api_key="",
            model="BAAI/bge-m3",
            provider="local",
        )
        result = embedder.embed(["hello", "world"])

        mock_st.assert_called_once_with("BAAI/bge-m3")
        mock_model.encode.assert_called_once_with(["hello", "world"])
        assert isinstance(result, np.ndarray)
        assert result.shape == (2, 768)

    @patch("peripatos_core.rag.embedder.SentenceTransformer")
    def test_local_embedder_raises_on_import_error(self, mock_st):
        """Local embedder raises EmbeddingError if sentence-transformers not available."""
        mock_st.side_effect = ModuleNotFoundError("No module named 'sentence_transformers'")

        with pytest.raises(EmbeddingError, match="sentence-transformers"):
            Embedder(
                base_url="",
                api_key="",
                model="BAAI/bge-m3",
                provider="local",
            )


class TestEmbedderConfig:
    """Config handling tests."""

    def test_config_default_rag_provider(self):
        """RAGConfig.provider defaults to openai_compatible."""
        from peripatos_core.config import RAGConfig
        config = RAGConfig()
        assert config.provider == "openai_compatible"
```

- [ ] **Step 2: Run tests — they should fail (Embedder doesn't accept provider yet)**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && pytest tests/test_embedder.py -v
```

Expected: FAIL — `Embedder.__init__` doesn't accept `provider` parameter.

- [ ] **Step 3: Commit**

```bash
git add tests/test_embedder.py
git commit -m "test: add dual-mode embedder tests (failing)"
```

---

### Task 4: Implement dual-mode Embedder

**Files:**
- Modify: `peripatos_core/rag/embedder.py`

- [ ] **Step 1: Implement dual-mode Embedder**

Replace the entire `Embedder` class in `embedder.py`:

```python
class Embedder:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        provider: str = "openai_compatible",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._provider = provider

        if provider == "local":
            self._init_local()
        else:
            self._local_model = None

    def _init_local(self) -> None:
        """Initialize local sentence-transformers model."""
        try:
            from sentence_transformers import SentenceTransformer
            self._local_model = SentenceTransformer(self._model)
        except ModuleNotFoundError as exc:
            raise EmbeddingError(
                "sentence-transformers is required for local embeddings. "
                f"Install it: pip install sentence-transformers ({exc})"
            ) from exc

    def embed(self, texts: list[str]) -> np.ndarray:
        if self._provider == "local":
            return self._embed_local(texts)
        return self._embed_remote(texts)

    def _embed_local(self, texts: list[str]) -> np.ndarray:
        """Encode texts using local sentence-transformers model."""
        embeddings = self._local_model.encode(texts)
        return np.array(embeddings, dtype=np.float32)

    def _embed_remote(self, texts: list[str]) -> np.ndarray:
        """Encode texts via OpenAI-compatible API."""
        all_embeddings: list[np.ndarray] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            try:
                resp = request_with_retry(
                    "POST",
                    f"{self._base_url}/embeddings",
                    json={"model": self._model, "input": batch},
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=60,
                )
            except requests.exceptions.RequestException as exc:
                raise EmbeddingError(f"Network error: {exc}") from exc
            if resp.status_code != 200:
                raise EmbeddingError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            data = resp.json()["data"]
            batch_emb = np.array(
                [item["embedding"] for item in data], dtype=np.float32
            )
            all_embeddings.append(batch_emb)
        if not all_embeddings:
            return np.empty((0, 0), dtype=np.float32)
        return np.vstack(all_embeddings)
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && pytest tests/test_embedder.py -v
```

Expected: All tests PASS.

- [ ] **Step 3: Run full test suite to verify no regressions**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && pytest tests/ --ignore=tests/test_e2e.py --ignore=tests/test_http_retry.py -m "not integration" --tb=short
```

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add peripatos_core/rag/embedder.py
git commit -m "feat: implement dual-mode Embedder (local + remote)"
```

---

### Task 5: Wire provider through DialogueGenerator

**Files:**
- Modify: `peripatos_core/dialogue.py`

- [ ] **Step 1: Pass provider to Embedder**

In `peripatos_core/dialogue.py`, find the `Embedder` constructor call in `DialogueGenerator.generate()` method and add the `provider` parameter. The current code is:

```python
embedder = Embedder(
    base_url=self._settings.llm.base_url,
    api_key=self._settings.llm.api_key,
    model=rag.embedding_model,
)
```

Change to:

```python
embedder = Embedder(
    base_url=self._settings.llm.base_url,
    api_key=self._settings.llm.api_key,
    model=rag.embedding_model,
    provider=rag.provider,
)
```

- [ ] **Step 2: Run tests to verify no regressions**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && pytest tests/test_dialogue.py -v
```

Expected: All tests PASS.

- [ ] **Step 3: Commit**

```bash
git add peripatos_core/dialogue.py
git commit -m "feat: pass rag.provider to Embedder in DialogueGenerator"
```

---

### Task 6: Update config tests and README docs

**Files:**
- Modify: `tests/test_config.py`
- Modify: `README.md`

- [ ] **Step 1: Add config test for rag.provider**

Add to `tests/test_config.py`:

```python
def test_rag_provider_defaults_to_openai_compatible():
    """RAGConfig.provider defaults to openai_compatible."""
    from peripatos_core.config import RAGConfig
    cfg = RAGConfig()
    assert cfg.provider == "openai_compatible"


def test_rag_provider_can_be_set_from_config():
    """rag.provider can be overridden via config file."""
    from peripatos_core.config import Settings, _apply_overrides
    settings = Settings()
    _apply_overrides(settings, {"rag": {"provider": "local", "embedding_model": "BAAI/bge-m3"}})
    assert settings.rag.provider == "local"
    assert settings.rag.embedding_model == "BAAI/bge-m3"
```

- [ ] **Step 2: Run config tests**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && pytest tests/test_config.py -v
```

Expected: All tests PASS.

- [ ] **Step 3: Update README.md RAG config table**

In the README.md RAG Configuration table, add a new row for `rag.provider`:

| Key | Default | Description |
|---|---|---|
| `rag.provider` | `"openai_compatible"` | Embedding backend: `"openai_compatible"` for API-based, `"local"` for `sentence-transformers` models. |
| `rag.embedding_model` | `"openai/text-embedding-3-small"` | Model name. For local mode: HuggingFace path (e.g., `"BAAI/bge-m3"`). For remote: API model identifier. |
| `rag.chunk_size` | `1000` | Size of text chunks for indexing (characters). |
| `rag.chunk_overlap` | `200` | Overlap between adjacent chunks (characters). |
| `rag.top_k` | `5` | Number of chunks to retrieve for each search query. |
| `rag.cache_dir` | `null` | Directory to store FAISS indices. Defaults to `~/.cache/peripatos/rag/`. |

- [ ] **Step 4: Run full test suite**

```bash
cd /Users/yzou/peripatos_workspace/peripatos && pytest tests/ --ignore=tests/test_e2e.py --ignore=tests/test_http_retry.py -m "not integration" --tb=short
```

Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/test_config.py README.md
git commit -m "docs: add rag.provider to config docs and test it"
```

---
