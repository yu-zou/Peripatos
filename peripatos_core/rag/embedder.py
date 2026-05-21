"""OpenAI-compatible embedder."""
from __future__ import annotations

import requests
import numpy as np

from peripatos_core.exceptions import EmbeddingError

BATCH_SIZE = 64


class Embedder:
    def __init__(self, base_url: str, api_key: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model

    def embed(self, texts: list[str]) -> np.ndarray:
        all_embeddings: list[np.ndarray] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i:i + BATCH_SIZE]
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
            except Exception as exc:
                raise EmbeddingError(f"Network error: {exc}") from exc
            if resp.status_code != 200:
                raise EmbeddingError(
                    f"HTTP {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()["data"]
            batch_emb = np.array(
                [item["embedding"] for item in data], dtype=np.float32
            )
            all_embeddings.append(batch_emb)
        return np.vstack(all_embeddings)
