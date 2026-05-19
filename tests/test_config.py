"""Tests for config loader."""

import json
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peripatos_core.config import Settings, load_settings  # pyright: ignore[reportMissingImports]
from peripatos_core.exceptions import ConfigError  # pyright: ignore[reportMissingImports]


def test_defaults_when_no_file(tmp_path, monkeypatch):
    """load_settings() with no files returns built-in defaults."""
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    settings = load_settings()
    assert isinstance(settings, Settings)
    assert settings.llm.model == "openai/gpt-4o-mini"
    assert settings.tts.provider == "edge"
    assert settings.defaults.archetype == "proxy_host"


def test_explicit_config_overrides(tmp_path, monkeypatch):
    """Explicit --config path overrides defaults."""
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"llm": {"model": "openai/gpt-4o", "api_key": "test-key"}}))
    settings = load_settings(config_path=cfg)
    assert settings.llm.model == "openai/gpt-4o"
    assert settings.llm.api_key == "test-key"
    assert settings.tts.provider == "edge"


def test_user_global_config(tmp_path, monkeypatch):
    """User global config is applied when present."""
    global_cfg = tmp_path / "config.json"
    global_cfg.write_text(json.dumps({"llm": {"api_key": "global-key"}}))
    monkeypatch.setattr("peripatos_core.config.USER_GLOBAL_CONFIG_PATH", global_cfg)
    settings = load_settings()
    assert settings.llm.api_key == "global-key"


def test_explicit_overrides_global(tmp_path, monkeypatch):
    """Explicit config takes priority over user global config."""
    global_cfg = tmp_path / "global.json"
    global_cfg.write_text(json.dumps({"llm": {"model": "global-model", "api_key": "global-key"}}))
    monkeypatch.setattr("peripatos_core.config.USER_GLOBAL_CONFIG_PATH", global_cfg)
    explicit_cfg = tmp_path / "explicit.json"
    explicit_cfg.write_text(json.dumps({"llm": {"model": "explicit-model"}}))
    settings = load_settings(config_path=explicit_cfg)
    assert settings.llm.model == "explicit-model"
    assert settings.llm.api_key == "global-key"


def test_missing_explicit_config_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    with pytest.raises(ConfigError, match="not found"):
        load_settings(config_path=tmp_path / "missing.json")


def test_unknown_keys_warn(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"llm": {"unknown_field": "value"}}))
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        load_settings(config_path=cfg)
    assert any("unknown_field" in str(warning.message) for warning in w)
