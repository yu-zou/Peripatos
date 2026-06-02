"""Dual-mode embedder — local (sentence-transformers) or remote (OpenAI-compatible API)."""
from __future__ import annotations

import logging

import numpy as np
import requests

from peripatos_core.exceptions import EmbeddingError
from peripatos_core.http import request_with_retry

logger = logging.getLogger(__name__)

BATCH_SIZE = 32

try:
    from sentence_transformers import SentenceTransformer
except ModuleNotFoundError:
    SentenceTransformer = None  # type: ignore[assignment]


class Embedder:
    def __init__(
        self,
        base_url: str = "",
        api_key: str = "",
        model: str = "",
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
            self._local_model = SentenceTransformer(self._model)
        except (ModuleNotFoundError, TypeError) as exc:
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
