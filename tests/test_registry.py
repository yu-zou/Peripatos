"""Tests for provider registry."""

import pytest

from peripatos_core.config import LLMConfig, TTSConfig
from peripatos_core.exceptions import ConfigError
from peripatos_core.providers.llm import OpenAICompatibleLLMProvider
from peripatos_core.providers.tts import EdgeTTSProvider, OpenAICompatibleTTSProvider
from peripatos_core.registry import build_llm_provider, build_tts_provider


def test_build_llm_provider_returns_openai_compatible():
    cfg = LLMConfig(base_url="https://router.requesty.ai/v1", api_key="test", model="gpt-4o-mini")
    provider = build_llm_provider(cfg)
    assert isinstance(provider, OpenAICompatibleLLMProvider)


def test_build_tts_edge_provider():
    cfg = TTSConfig(provider="edge", voice="en-US-AriaNeural")
    provider = build_tts_provider(cfg)
    assert isinstance(provider, EdgeTTSProvider)


def test_build_tts_openai_compatible_provider():
    cfg = TTSConfig(provider="openai_compatible", base_url="https://api.openai.com/v1", api_key="test")
    provider = build_tts_provider(cfg)
    assert isinstance(provider, OpenAICompatibleTTSProvider)


def test_build_tts_openai_compatible_missing_base_url_raises():
    cfg = TTSConfig(provider="openai_compatible", base_url="", api_key="test")
    with pytest.raises(ConfigError, match="base_url"):
        build_tts_provider(cfg)


def test_build_tts_unknown_provider_raises():
    cfg = TTSConfig(provider="elevenlabs")
    with pytest.raises(ConfigError, match="Unknown TTS provider"):
        build_tts_provider(cfg)


def test_build_tts_case_insensitive():
    cfg = TTSConfig(provider="EDGE", voice="en-US-AriaNeural")
    provider = build_tts_provider(cfg)
    assert isinstance(provider, EdgeTTSProvider)
