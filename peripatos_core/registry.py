"""Provider registry — factory functions to build providers from Settings."""
from __future__ import annotations

# pyright: reportUnusedFunction=false

from typing import Any

from peripatos_core.config import LLMConfig, Settings, TTSConfig, get_default_voices
from peripatos_core.exceptions import ConfigError
from peripatos_core.providers.llm import LLMProvider, OpenAICompatibleLLMProvider
from peripatos_core.providers.tts import (
    EdgeTTSProvider,
    OpenAICompatibleTTSProvider,
    TTSProvider,
)


# Provider-aware default voice pairs
DEFAULT_VOICES: dict[str, tuple[str, str]] = {
    "edge": ("en-US-GuyNeural", "en-US-AriaNeural"),
    "openai_compatible": ("onyx", "nova"),
}


def _resolve_voice_slots(settings: "Settings", language: str = "en") -> tuple[str, str, str]:
    """Resolve (host_voice, interviewee_voice, source) from settings.

    Resolution order:
    1. tts.voices.host / tts.voices.interviewee  (explicit config)
    2. tts.voice (legacy single-voice — both speakers get same voice)
    3. Language-aware defaults via get_default_voices(language)  (edge provider)
       or DEFAULT_VOICES[provider]  (other providers)

    Returns:
        (host_voice, interviewee_voice, source) where source is one of:
        "config", "legacy", "default"
    """
    import warnings

    provider = settings.tts.provider.lower()
    if provider == "edge":
        lang_defaults = get_default_voices(language)
        defaults: tuple[str, str] = (lang_defaults["host"], lang_defaults["interviewee"])
    else:
        defaults = DEFAULT_VOICES.get(provider, DEFAULT_VOICES["edge"])

    voices = settings.tts.voices
    if isinstance(voices, dict):
        host_cfg = voices.get("host")
        interviewee_cfg = voices.get("interviewee")
    else:
        host_cfg = voices.host
        interviewee_cfg = voices.interviewee

    if host_cfg or interviewee_cfg:
        # At least one explicit voice configured
        host_voice = host_cfg or defaults[0]
        interviewee_voice = interviewee_cfg or defaults[1]
        source = "config"
        if host_voice == interviewee_voice:
            warnings.warn(
                "tts.voices.host and tts.voices.interviewee are the same voice — "
                "both speakers will sound identical",
                stacklevel=2,
            )
    elif (
        not host_cfg
        and not interviewee_cfg
        and (settings.tts._voice_explicitly_set or settings.tts.voice != "en-US-AriaNeural")
    ):
        # Legacy path: tts.voice was explicitly set or manually overridden
        if settings.tts.voice != "en-US-AriaNeural" and not settings.tts._voice_explicitly_set:
            warnings.warn(
                "tts.voice is deprecated; use tts.voices.host and tts.voices.interviewee instead. "
                "Both speakers will use the same voice.",
                DeprecationWarning,
                stacklevel=2,
            )
        host_voice = settings.tts.voice
        interviewee_voice = settings.tts.voice
        source = "legacy"
    else:
        # Provider-aware defaults
        host_voice = defaults[0]
        interviewee_voice = defaults[1]
        source = "default"

    if language == "zh-CN":
        if "en-US" in host_voice or "en-US" in interviewee_voice:
            warnings.warn(
                "Language is zh-CN but TTS voice is English — audio quality may degrade",
                stacklevel=2,
            )

    return host_voice, interviewee_voice, source


def build_voice_map(settings: "Settings", archetype_prompt: Any, language: str = "en") -> dict[str, str]:
    """Build a voice_map dict for AudioRenderer from settings and archetype.

    Keys are the speaker names from the archetype (host_name, guest_name).
    Values are the resolved TTS voice strings.

    Args:
        settings: Loaded Settings object.
        archetype_prompt: The loaded ArchetypePrompt for the current archetype.
        language: BCP-47 language tag for voice default selection (e.g. "en", "zh-CN").

    Returns:
        dict mapping speaker name → voice string.
    """
    host_voice, interviewee_voice, _ = _resolve_voice_slots(settings, language=language)
    return {
        archetype_prompt.host_name: host_voice,
        archetype_prompt.guest_name: interviewee_voice,
    }

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
