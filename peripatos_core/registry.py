"""Provider registry — factory functions to build providers from Settings."""
from __future__ import annotations

from peripatos_core.config import LLMConfig, Settings, TTSConfig
from peripatos_core.exceptions import ConfigError
from peripatos_core.providers.llm import LLMProvider, OpenAICompatibleLLMProvider
from peripatos_core.providers.tts import (
    EdgeTTSProvider,
    OpenAICompatibleTTSProvider,
    TTSProvider,
)


def build_llm_provider(cfg: LLMConfig) -> LLMProvider:
    """Build an LLM provider from config.

    Currently only OpenAICompatibleLLMProvider is supported.
    """
    return OpenAICompatibleLLMProvider(cfg)


def build_tts_provider(cfg: TTSConfig) -> TTSProvider:
    """Build a TTS provider from config.

    Supported providers:
    - "edge" (default): EdgeTTSProvider — no API key required
    - "openai_compatible": OpenAICompatibleTTSProvider — requires base_url + api_key
    """
    provider = cfg.provider.lower()
    if provider == "edge":
        return EdgeTTSProvider(cfg)
    elif provider == "openai_compatible":
        if not cfg.base_url:
            raise ConfigError("TTS provider 'openai_compatible' requires tts.base_url")
        return OpenAICompatibleTTSProvider(cfg)
    else:
        raise ConfigError(
            f"Unknown TTS provider: {cfg.provider!r}. Supported: 'edge', 'openai_compatible'"
        )


def build_providers_from_settings(settings: Settings) -> tuple[LLMProvider, TTSProvider]:
    """Convenience function: build both providers from a Settings object."""
    llm = build_llm_provider(settings.llm)
    tts = build_tts_provider(settings.tts)
    return llm, tts
