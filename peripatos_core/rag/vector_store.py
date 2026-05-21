"""FAISS vector store with disk cache."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from peripatos_core.exceptions import RetrievalError
from peripatos_core.rag.chunker import Chunk


class VectorStore:
    def __init__(self, cache_dir: Path, content_hash: str, dim: int | None = None) -> None:
        self.cache_dir = cache_dir
        self.content_hash = content_hash
        self.dim = dim
        self.store_dir = cache_dir / content_hash[:16]
        self.index_path = self.store_dir / "index.faiss"
        self.mapping_path = self.store_dir / "mapping.json"
        self.index: faiss.Index | None = None
        self.mapping: dict[str, dict[str, Any]] = {}

    def has_cache(self) -> bool:
        return self.index_path.exists() and self.mapping_path.exists()

    def load(self) -> None:
        if not self.has_cache():
            raise RetrievalError(f"Vector store cache not found: {self.store_dir}")
        try:
            index = faiss.read_index(str(self.index_path))
            self.index = index
            self.dim = index.d
            self.mapping = json.loads(self.mapping_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RetrievalError(f"Failed to load vector store cache: {exc}") from exc

    def build(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        if embeddings.ndim != 2:
            raise RetrievalError("Embeddings must have shape (N, dim)")
        if len(chunks) != embeddings.shape[0]:
            raise RetrievalError("Chunk count must match embedding row count")

        dim = self.dim or embeddings.shape[1]
        if embeddings.shape[1] != dim:
            raise RetrievalError(
                f"Embedding dimension {embeddings.shape[1]} does not match vector store dim {dim}"
            )

        index = faiss.IndexFlatL2(dim)
        index.add(embeddings.astype(np.float32))

        mapping = {
            str(chunk.id): {
                "text": chunk.text,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "section_hint": chunk.section_hint,
            }
            for chunk in chunks
        }

        self.store_dir.mkdir(parents=True, exist_ok=True)
        index_tmp = Path(f"{self.index_path}.tmp")
        mapping_tmp = Path(f"{self.mapping_path}.tmp")
        try:
            faiss.write_index(index, str(index_tmp))
            mapping_tmp.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
            os.replace(index_tmp, self.index_path)
            os.replace(mapping_tmp, self.mapping_path)
        except Exception as exc:
            index_tmp.unlink(missing_ok=True)
            mapping_tmp.unlink(missing_ok=True)
            raise RetrievalError(f"Failed to build vector store cache: {exc}") from exc

        self.index = index
        self.mapping = mapping
        self.dim = dim

    def search(self, query_embedding: np.ndarray, k: int = 5) -> list[tuple[int, float, str]]:
        if self.index is None:
            raise RetrievalError("Vector store index is not loaded")
        query = query_embedding.reshape(1, -1).astype(np.float32)
        if query.shape[1] != self.index.d:
            raise RetrievalError(
                f"Query dimension {query.shape[1]} does not match vector store dim {self.index.d}"
            )
        distances, indices = self.index.search(query, k)
        results: list[tuple[int, float, str]] = []
        chunk_ids = list(self.mapping)
        for idx, distance in zip(indices[0], distances[0], strict=True):
            row_id = int(idx)
            if row_id < 0:
                continue
            try:
                chunk_id = int(chunk_ids[row_id])
            except IndexError as exc:
                raise RetrievalError(f"Search returned unknown index row: {row_id}") from exc
            entry = self.get_chunk(chunk_id)
            results.append((chunk_id, float(distance), entry["text"]))
        return results

    def get_chunk(self, chunk_id: int) -> dict[str, Any]:
        try:
            return self.mapping[str(chunk_id)]
        except KeyError as exc:
            raise RetrievalError(f"Chunk not found: {chunk_id}") from exc

    def list_sections(self) -> list[tuple[int, str]]:
        sections: list[tuple[int, str]] = []
        for chunk_id, entry in self.mapping.items():
            section_hint = entry.get("section_hint")
            if section_hint is not None:
                sections.append((int(chunk_id), section_hint))
        return sections
