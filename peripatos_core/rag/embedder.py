"""OpenAI-compatible embedder."""
from __future__ import annotations

import logging
import random
import time

import requests
import numpy as np

from peripatos_core.exceptions import EmbeddingError

logger = logging.getLogger(__name__)

BATCH_SIZE = 32  # was 64

_MAX_RETRIES = 5
_BASE_DELAY = 1.0
_RETRYABLE_HTTP_CODES = frozenset({429, 500, 502, 503, 504})


class Embedder:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model

    def _post_with_retry(self, batch: list[str]) -> list[dict]:
        """POST a single embedding batch with retry + full-jitter backoff."""
        last_exc: Exception | None = None
        last_status: int | None = None
        last_body: str = ""
        for attempt in range(_MAX_RETRIES):
            try:
                resp = requests.post(
                    f"{self._base_url}/embeddings",
                    json={"model": self._model, "input": batch},
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=60,
                )
            except (
                requests.exceptions.SSLError,
                requests.exceptions.ConnectionError,
                requests.exceptions.Timeout,
            ) as exc:
                last_exc = exc
                delay = random.uniform(0, _BASE_DELAY * (2 ** attempt))
                logger.warning(
                    "Embedding retry attempt=%d/%d reason=%s: %s (sleeping %.1fs)",
                    attempt + 1, _MAX_RETRIES, type(exc).__name__, exc, delay,
                )
                time.sleep(delay)
                continue
            if resp.status_code == 200:
                return resp.json()["data"]
            if resp.status_code in _RETRYABLE_HTTP_CODES:
                last_status = resp.status_code
                last_body = resp.text
                delay = random.uniform(0, _BASE_DELAY * (2 ** attempt))
                logger.warning(
                    "Embedding retry attempt=%d/%d HTTP %d (sleeping %.1fs)",
                    attempt + 1, _MAX_RETRIES, resp.status_code, delay,
                )
                time.sleep(delay)
                continue
            # Non-retryable HTTP error → fail immediately
            raise EmbeddingError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        # All attempts exhausted
        if last_exc is not None:
            raise EmbeddingError(f"Network error: {last_exc}") from last_exc
        raise EmbeddingError(
            f"HTTP {last_status} after {_MAX_RETRIES} retries: {last_body[:200]}"
        )

    def embed(self, texts: list[str]) -> np.ndarray:
        all_embeddings: list[np.ndarray] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            data = self._post_with_retry(batch)
            batch_emb = np.array(
                [item["embedding"] for item in data], dtype=np.float32
            )
            all_embeddings.append(batch_emb)
        if not all_embeddings:
            return np.empty((0, 0), dtype=np.float32)
        return np.vstack(all_embeddings)
