"""JSON configuration loader for Peripatos Core.

Resolution chain (highest priority first):
  1. --config PATH (CLI argument)
  2. ~/.config/peripatos/config.json (user global)
  3. Built-in defaults
"""
from __future__ import annotations

import json
import logging
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

USER_GLOBAL_CONFIG_PATH = Path.home() / ".config" / "peripatos" / "config.json"

KNOWN_KEYS = {"llm", "tts", "defaults", "rag"}
KNOWN_LLM_KEYS = {"base_url", "api_key", "model"}
KNOWN_RAG_KEYS = {"provider", "embedding_model", "chunk_size", "chunk_overlap", "top_k", "cache_dir"}
KNOWN_TTS_KEYS = {"provider", "base_url", "api_key", "voice", "model", "voices"}
KNOWN_TTS_VOICES_KEYS = {"host", "interviewee"}
KNOWN_DEFAULTS_KEYS = {"archetype", "output_dir", "language"}


@dataclass
class LLMConfig:
    base_url: str = "https://router.requesty.ai/v1"
    api_key: str = ""
    model: str = "openai/gpt-4o-mini"


@dataclass
class RAGConfig:
    provider: str = "openai_compatible"
    embedding_model: str = "openai/text-embedding-3-small"
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k: int = 5
    cache_dir: str | None = None


@dataclass
class TTSVoices:
    host: str = ""
    interviewee: str = ""

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __contains__(self, key: object) -> bool:
        return isinstance(key, str) and getattr(self, key, "") != ""

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TTSVoices):
            return self.host == other.host and self.interviewee == other.interviewee
        if isinstance(other, dict):
            return {k: v for k, v in {"host": self.host, "interviewee": self.interviewee}.items() if v} == other
        return NotImplemented


@dataclass
class TTSConfig:
    provider: str = "edge"
    base_url: str = ""
    api_key: str = ""
    voice: str = "en-US-AriaNeural"
    model: str = "tts-1"
    voices: TTSVoices = field(default_factory=TTSVoices)
    _voice_explicitly_set: bool = field(default=False, repr=False, compare=False)


@dataclass
class Defaults:
    archetype: str = "peer"
    output_dir: str = "."
    language: str = "en"


SUPPORTED_LANGUAGES = {"en", "zh-CN"}

LANGUAGE_INSTRUCTIONS = {
    "en": "Respond in English.",
    "zh-CN": "Respond in Mandarin Chinese (简体中文). Keep technical terms, acronyms, and proper nouns (e.g., 'Transformer', 'Attention Mechanism', 'RAG') in English. Use natural bilingual code-switching.",
}


def get_language_instruction(language: str) -> str:
    """Return the language instruction for LLM prompts."""
    if language not in SUPPORTED_LANGUAGES:
        import warnings
        warnings.warn(
            f"Unsupported language '{language}' — falling back to English",
            stacklevel=2,
        )
        return LANGUAGE_INSTRUCTIONS["en"]
    return LANGUAGE_INSTRUCTIONS[language]


LANGUAGE_VOICES: dict[str, dict[str, str]] = {
    "en": {"host": "en-US-GuyNeural", "interviewee": "en-US-AriaNeural"},
    "zh-CN": {"host": "zh-CN-YunxiNeural", "interviewee": "zh-CN-XiaoxiaoNeural"},
}


def get_default_voices(language: str) -> dict[str, str]:
    """Return default TTS voices for the given language."""
    return LANGUAGE_VOICES.get(language, LANGUAGE_VOICES["en"])


@dataclass
class Settings:
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    defaults: Defaults = field(default_factory=Defaults)
    rag: RAGConfig = field(default_factory=RAGConfig)


def _warn_unknown(section: str, data: dict[str, Any], known: set[str]) -> None:
    for key in data:
        if key not in known:
            warnings.warn(f"Unknown config key '{section}.{key}' — ignored", stacklevel=3)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _apply_overrides(settings: Settings, data: dict[str, Any]) -> None:
    """Merge a config dict into settings in-place."""
    for key in data:
        if key not in KNOWN_KEYS:
            warnings.warn(f"Unknown top-level config key '{key}' — ignored", stacklevel=3)

    if "llm" in data:
        llm_data = data["llm"]
        _warn_unknown("llm", llm_data, KNOWN_LLM_KEYS)
        for k in KNOWN_LLM_KEYS:
            if k in llm_data:
                setattr(settings.llm, k, llm_data[k])

    if "rag" in data:
        rag_data = data["rag"]
        _warn_unknown("rag", rag_data, KNOWN_RAG_KEYS)
        for k in KNOWN_RAG_KEYS:
            if k in rag_data:
                setattr(settings.rag, k, rag_data[k])

    if "tts" in data:
        tts_data = data["tts"]
        _warn_unknown("tts", tts_data, KNOWN_TTS_KEYS)
        for k in KNOWN_TTS_KEYS - {"voices"}:
            if k in tts_data:
                setattr(settings.tts, k, tts_data[k])
        if "voice" in tts_data:
            settings.tts._voice_explicitly_set = True
        if "voices" in tts_data:
            voices_data = tts_data["voices"]
            if isinstance(voices_data, dict):
                _warn_unknown("tts.voices", voices_data, KNOWN_TTS_VOICES_KEYS)
                for vk in KNOWN_TTS_VOICES_KEYS:
                    if vk in voices_data:
                        setattr(settings.tts.voices, vk, voices_data[vk])
            else:
                warnings.warn("tts.voices must be a dict — ignored", stacklevel=3)

    if "defaults" in data:
        def_data = data["defaults"]
        _warn_unknown("defaults", def_data, KNOWN_DEFAULTS_KEYS)
        for k in KNOWN_DEFAULTS_KEYS:
            if k in def_data:
                setattr(settings.defaults, k, def_data[k])


def load_settings(config_path: Path | None = None) -> Settings:
    """Load settings using the resolution chain.

    Args:
        config_path: Explicit path from --config CLI flag (highest priority).

    Returns:
        Fully resolved Settings instance.
    """
    settings = Settings()

    if USER_GLOBAL_CONFIG_PATH.exists():
        logger.debug("Loading user global config: %s", USER_GLOBAL_CONFIG_PATH)
        _apply_overrides(settings, _load_json(USER_GLOBAL_CONFIG_PATH))

    if config_path is not None:
        if not config_path.exists():
            from peripatos_core.exceptions import ConfigError  # pyright: ignore[reportMissingImports]

            raise ConfigError(f"Config file not found: {config_path}")
        logger.debug("Loading explicit config: %s", config_path)
        _apply_overrides(settings, _load_json(config_path))

    if settings.tts._voice_explicitly_set and not settings.tts.voices.host and not settings.tts.voices.interviewee:
        warnings.warn(
            "tts.voice is deprecated; use tts.voices.host and tts.voices.interviewee instead. "
            "Both speakers will use the same voice.",
            DeprecationWarning,
            stacklevel=2,
        )

    return settings
