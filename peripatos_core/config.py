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

KNOWN_KEYS = {"llm", "tts", "defaults", "parser"}
KNOWN_LLM_KEYS = {"base_url", "api_key", "model"}
KNOWN_TTS_KEYS = {"provider", "base_url", "api_key", "voice", "model"}
KNOWN_DEFAULTS_KEYS = {"archetype", "output_dir"}
KNOWN_PARSER_KEYS = {"backend"}


@dataclass
class LLMConfig:
    base_url: str = "https://router.requesty.ai/v1"
    api_key: str = ""
    model: str = "openai/gpt-4o-mini"


@dataclass
class TTSConfig:
    provider: str = "edge"
    base_url: str = ""
    api_key: str = ""
    voice: str = "en-US-AriaNeural"
    model: str = "tts-1"


@dataclass
class Defaults:
    archetype: str = "peer"
    output_dir: str = "."


@dataclass
class ParserConfig:
    backend: str = "docling"


@dataclass
class Settings:
    llm: LLMConfig = field(default_factory=LLMConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    defaults: Defaults = field(default_factory=Defaults)
    parser: ParserConfig = field(default_factory=ParserConfig)


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

    if "tts" in data:
        tts_data = data["tts"]
        _warn_unknown("tts", tts_data, KNOWN_TTS_KEYS)
        for k in KNOWN_TTS_KEYS:
            if k in tts_data:
                setattr(settings.tts, k, tts_data[k])

    if "defaults" in data:
        def_data = data["defaults"]
        _warn_unknown("defaults", def_data, KNOWN_DEFAULTS_KEYS)
        for k in KNOWN_DEFAULTS_KEYS:
            if k in def_data:
                setattr(settings.defaults, k, def_data[k])

    if "parser" in data:
        parser_data = data["parser"]
        _warn_unknown("parser", parser_data, KNOWN_PARSER_KEYS)
        for k in KNOWN_PARSER_KEYS:
            if k in parser_data:
                setattr(settings.parser, k, parser_data[k])


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

    return settings
