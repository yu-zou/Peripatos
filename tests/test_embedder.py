"""Tests for dual-mode Embedder (local vs remote)."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from peripatos_core.config import RAGConfig, Settings, _apply_overrides
from peripatos_core.exceptions import EmbeddingError
from peripatos_core.rag.embedder import Embedder


class TestRemoteEmbedder:
    def test_remote_embedder_calls_api(self, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}],
        }
        mock_request = MagicMock(return_value=mock_resp)
        monkeypatch.setattr(
            "peripatos_core.rag.embedder.request_with_retry", mock_request
        )

        embedder = Embedder(
            provider="openai_compatible",
            base_url="http://test/v1",
            api_key="key",
            model="test-model",
        )
        result = embedder.embed(["hello world"])

        mock_request.assert_called_once()
        call_args, call_kwargs = mock_request.call_args
        assert call_args[0] == "POST"
        assert call_args[1] == "http://test/v1/embeddings"
        assert call_kwargs["json"] == {
            "model": "test-model",
            "input": ["hello world"],
        }
        assert call_kwargs["headers"]["Authorization"] == "Bearer key"
        assert call_kwargs["headers"]["Content-Type"] == "application/json"
        assert isinstance(result, np.ndarray)
        np.testing.assert_array_equal(result, np.array([[0.1, 0.2, 0.3]], dtype=np.float32))

    def test_remote_embedder_is_default(self):
        embedder = Embedder()
        assert embedder._provider == "openai_compatible"


class TestLocalEmbedder:
    def test_local_embedder_calls_encode(self):
        import peripatos_core.rag.embedder as embedder_module

        mock_model = MagicMock()
        mock_model.encode.return_value = np.array(
            [[0.1, 0.2, 0.3]], dtype=np.float32
        )
        mock_st_cls = MagicMock(return_value=mock_model)
        embedder_module.SentenceTransformer = mock_st_cls

        embedder = Embedder(provider="local", model="BAAI/bge-m3")
        result = embedder.embed(["hello world"])

        mock_st_cls.assert_called_once_with("BAAI/bge-m3")
        mock_model.encode.assert_called_once_with(["hello world"])
        assert isinstance(result, np.ndarray)

    def test_local_embedder_raises_on_import_error(self):
        import peripatos_core.rag.embedder as embedder_module

        mock_st_cls = MagicMock()
        mock_st_cls.side_effect = ModuleNotFoundError(
            "No module named 'sentence_transformers'"
        )
        embedder_module.SentenceTransformer = mock_st_cls

        with pytest.raises(EmbeddingError, match="sentence-transformers"):
            Embedder(provider="local", model="BAAI/bge-m3")


class TestEmbedderConfig:
    def test_config_default_rag_provider(self):
        assert RAGConfig().provider == "openai_compatible"

    def test_rag_provider_can_be_set_from_config(self):
        settings = Settings()
        _apply_overrides(
            settings,
            {"rag": {"provider": "local", "embedding_model": "BAAI/bge-m3"}},
        )
        assert settings.rag.provider == "local"
        assert settings.rag.embedding_model == "BAAI/bge-m3"
