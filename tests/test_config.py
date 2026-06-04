"""Tests for config loader."""

import json
import sys
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peripatos_core.config import ParserConfig, TTSVoices, Settings, load_settings  # pyright: ignore[reportMissingImports]
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
    assert settings.archetype == "peer"


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


# ── Task 4: TDD red phase — voices parsing ──────────────────────────────────

def test_voices_parsed_from_config(tmp_path, monkeypatch):
    """tts.voices.host and tts.voices.interviewee are loaded into TTSConfig.voices."""
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "tts": {"voices": {"host": "en-US-GuyNeural", "interviewee": "en-US-AriaNeural"}}
    }))
    settings = load_settings(config_path=cfg)
    assert settings.tts.voices.get("host") == "en-US-GuyNeural"
    assert settings.tts.voices.get("interviewee") == "en-US-AriaNeural"


def test_voices_partial_override_uses_defaults(tmp_path, monkeypatch):
    """Only tts.voices.host set — interviewee falls back to provider default."""
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"tts": {"voices": {"host": "en-US-GuyNeural"}}}))
    settings = load_settings(config_path=cfg)
    assert settings.tts.voices.get("host") == "en-US-GuyNeural"
    # interviewee not set in config — voices dict should not have it
    assert "interviewee" not in settings.tts.voices


def test_voices_unknown_key_warns(tmp_path, monkeypatch):
    """Unknown key inside tts.voices emits a warning."""
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"tts": {"voices": {"host": "en-US-GuyNeural", "narrator": "bad"}}}))
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        load_settings(config_path=cfg)
    assert any("narrator" in str(warning.message) for warning in w)


def test_voices_non_dict_warns(tmp_path, monkeypatch):
    """tts.voices set to a non-dict value emits a warning and is ignored."""
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"tts": {"voices": "bad-value"}}))
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        settings = load_settings(config_path=cfg)
    assert any("must be a dict" in str(warning.message) for warning in w)
    assert settings.tts.voices == {}


# ── Task 2: Language instruction constants and prompt placeholders ──────────


def test_get_default_voices_en():
    from peripatos_core.config import get_default_voices
    voices = get_default_voices("en")
    assert voices["host"] == "en-US-GuyNeural"
    assert voices["interviewee"] == "en-US-AriaNeural"


def test_get_default_voices_zh_cn():
    from peripatos_core.config import get_default_voices
    voices = get_default_voices("zh-CN")
    assert voices["host"] == "zh-CN-YunxiNeural"
    assert voices["interviewee"] == "zh-CN-XiaoxiaoNeural"


def test_get_default_voices_unknown_falls_back_to_en():
    from peripatos_core.config import get_default_voices
    voices = get_default_voices("fr")
    assert voices == get_default_voices("en")


def test_host_questions_has_language_placeholder():
    from pathlib import Path
    text = Path("peripatos_core/prompts/host_questions.txt").read_text()
    assert "{language_instruction}" in text


def test_react_system_has_language_placeholder():
    from pathlib import Path
    text = Path("peripatos_core/prompts/react_system.txt").read_text()
    assert "{language_instruction}" in text


# ── Task 5: TDD — language field ─────────────────────────────────────────────


def test_defaults_language_is_english_by_default():
    s = Settings()
    assert s.language == "en"


def test_config_parses_language_zh_cn_top_level():
    from peripatos_core.config import Settings, _apply_overrides

    s = Settings()
    _apply_overrides(s, {"language": "zh-CN"})
    assert s.language == "zh-CN"


def test_config_parses_archetype_and_output_dir_top_level():
    from peripatos_core.config import Settings, _apply_overrides

    s = Settings()
    _apply_overrides(s, {"archetype": "tutor", "output_dir": "/tmp"})
    assert s.archetype == "tutor"
    assert s.output_dir == "/tmp"


def test_defaults_section_still_works_with_deprecation_warning():
    from peripatos_core.config import Settings, _apply_overrides

    s = Settings()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _apply_overrides(s, {"defaults": {"language": "zh-CN", "archetype": "skeptic"}})
    assert s.language == "zh-CN"
    assert s.archetype == "skeptic"
    deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
    assert len(deprecation_warnings) >= 1
    assert any("deprecated" in str(x.message) for x in deprecation_warnings)


def test_top_level_fields_preferred_defaults_deprecated():
    from peripatos_core.config import Settings, _apply_overrides

    s = Settings()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        _apply_overrides(s, {"language": "zh-CN", "defaults": {"language": "en"}})
    # Top-level fields take precedence over the deprecated "defaults" section
    assert s.language == "zh-CN"
    deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
    assert len(deprecation_warnings) >= 1


def test_get_language_instruction_zh_cn():
    from peripatos_core.config import get_language_instruction

    instr = get_language_instruction("zh-CN")
    assert "Mandarin" in instr
    assert "English" in instr


def test_get_language_instruction_en():
    from peripatos_core.config import get_language_instruction

    instr = get_language_instruction("en")
    assert "English" in instr


def test_unknown_language_warns_and_falls_back():
    import warnings

    from peripatos_core.config import get_language_instruction

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        instr = get_language_instruction("fr")
        assert len(w) == 1
        assert "Unsupported language" in str(w[0].message)
        assert instr == get_language_instruction("en")


# ── Task 6: RAG provider config ──────────────────────────────────────────────


def test_rag_provider_defaults_to_openai_compatible():
    from peripatos_core.config import RAGConfig
    cfg = RAGConfig()
    assert cfg.provider == "openai_compatible"


def test_rag_provider_can_be_set_from_config(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "rag": {"provider": "local", "embedding_model": "BAAI/bge-m3"}
    }))
    settings = load_settings(config_path=cfg)
    assert settings.rag.provider == "local"
    assert settings.rag.embedding_model == "BAAI/bge-m3"


# ── Parser config ──────────────────────────────────────────────

def test_parser_config_defaults():
    from peripatos_core.config import ParserConfig
    cfg = ParserConfig()
    assert cfg.mineru_token == ""


def test_parser_token_loaded_from_config(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"parser": {"mineru_token": "test-token-123"}}))
    settings = load_settings(config_path=cfg)
    assert settings.parser.mineru_token == "test-token-123"


def test_parser_unknown_key_warns(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"parser": {"unknown_field": "value"}}))
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        load_settings(config_path=cfg)
    assert any("unknown_field" in str(warning.message) for warning in w)


# ── TTSVoices class tests ─────────────────────────────────────────────


def test_tts_voices_get_returns_value():
    assert TTSVoices().get("host") == ""
    assert TTSVoices().get("interviewee") == ""
    assert TTSVoices(host="en-US-GuyNeural").get("host") == "en-US-GuyNeural"
    assert TTSVoices(interviewee="en-US-AriaNeural").get("interviewee") == "en-US-AriaNeural"
    assert TTSVoices().get("nonexistent", "fallback") == "fallback"


def test_tts_voices_contains():
    assert "host" in TTSVoices(host="en-US-GuyNeural")
    assert "interviewee" in TTSVoices(interviewee="en-US-AriaNeural")
    assert "host" not in TTSVoices()
    assert "interviewee" not in TTSVoices()
    assert "host" not in TTSVoices(host="")


def test_tts_voices_eq_dict():
    assert TTSVoices(host="A", interviewee="B") == {"host": "A", "interviewee": "B"}
    assert TTSVoices(host="A") == {"host": "A"}
    assert TTSVoices(interviewee="B") == {"interviewee": "B"}
    assert TTSVoices() == {}


def test_tts_voices_eq_other_ttsvoices():
    voices1 = TTSVoices(host="A", interviewee="B")
    voices2 = TTSVoices(host="A", interviewee="B")
    assert voices1 == voices2
    assert TTSVoices() == TTSVoices()
    assert TTSVoices(host="X") != TTSVoices(host="Y")


def test_tts_voices_eq_non_matching():
    assert TTSVoices().__eq__("not a dict or TTSVoices") is NotImplemented
    assert TTSVoices().__eq__(123) is NotImplemented


# ── Config edge cases ─────────────────────────────────────────────────


def test_unknown_top_level_key_warns(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"fantasy_key": "some_value"}))
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        load_settings(config_path=cfg)
    assert any("fantasy_key" in str(warning.message) for warning in w)


def test_empty_config_file_returns_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({}))
    settings = load_settings(config_path=cfg)
    assert settings.llm.model == "openai/gpt-4o-mini"
    assert settings.tts.provider == "edge"
    assert settings.archetype == "peer"
    assert settings.language == "en"
    assert settings.output_dir == "."


def test_load_settings_invalid_json_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json"
    )
    cfg = tmp_path / "config.json"
    cfg.write_text("not valid json {{{")
    with pytest.raises(json.JSONDecodeError):
        load_settings(config_path=cfg)


def test_parser_config_in_settings():
    settings = Settings()
    assert isinstance(settings.parser, ParserConfig)
    assert settings.parser.mineru_token == ""
