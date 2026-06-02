# Dual-Mode Embedder — Design Spec

## Goal
Allow `rag.embedding_model` to use either a local `sentence-transformers` model or a remote OpenAI-compatible API, controlled by a new `rag.provider` config key.

## Config Schema

Add `rag.provider` to the RAG config with two valid values:

| Value | Behavior |
|---|---|
| `"openai_compatible"` (default) | HTTP POST to `llm.base_url` with `rag.embedding_model` as the model name |
| `"local"` | Load `sentence-transformers` locally with `rag.embedding_model` as the HuggingFace model name |

## Changes

### 1. `peripatos_core/config.py`

`RAGConfig` gets a new `provider` field:

```python
@dataclass
class RAGConfig:
    provider: str = "openai_compatible"
    embedding_model: str = "openai/text-embedding-3-small"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5
    cache_dir: str | None = None
```

Add `"provider"` to `KNOWN_RAG_KEYS`. In `_apply_overrides()`, set `settings.rag.provider` from config data.

### 2. `peripatos_core/rag/embedder.py`

Constructor takes a new `provider: str` parameter. Mode is determined at init time:

**Local mode** (`provider == "local"`):
```python
from sentence_transformers import SentenceTransformer
self._model = SentenceTransformer(model)
```
`embed()` calls `self._model.encode(texts)` → `np.array`.

**Remote mode** (`provider == "openai_compatible"`):
Current behavior — HTTP POST to `base_url/embeddings`.

**Error handling:**
- `sentence-transformers` not installed → `EmbeddingError("sentence-transformers is required for local embeddings. Install it: pip install sentence-transformers")`
- Invalid model / download failure → `EmbeddingError` with model name and hint to check network

### 3. `peripatos_core/dialogue.py`

Pass `settings.rag.provider` to `Embedder` constructor:

```python
embedder = Embedder(
    base_url=self._settings.llm.base_url,
    api_key=self._settings.llm.api_key,
    model=rag.embedding_model,
    provider=rag.provider,
)
```

### 4. `pyproject.toml`

Add `sentence-transformers` to dependencies.

### 5. Tests

New `test_embedder.py`:
- `test_local_embedder_uses_sentence_transformers` — mocks `SentenceTransformer`, verifies `embed()` calls `encode()`
- `test_local_embedder_raises_on_missing_library` — patches import to fail, verifies `EmbeddingError`
- `test_remote_embedder_unchanged` — verifies current remote behavior still works
- Update `config.py` tests to verify `rag.provider` defaults to `"openai_compatible"` and can be set from config

## Dependencies

- `sentence-transformers` — added to `pyproject.toml` as required dependency
- BGE-m3 weights downloaded on first use, cached in `~/.cache/huggingface/`

## Backward Compatibility

Default `rag.provider = "openai_compatible"` means existing configs work unchanged. Users who want local embeddings must explicitly set `rag.provider = "local"` and choose a model name like `"BAAI/bge-m3"`.
