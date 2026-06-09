"""Tests for registry.py — build_voice_map and _resolve_voice_slots."""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from peripatos_core.config import Settings  # pyright: ignore
from peripatos_core.registry import (  # pyright: ignore
    _resolve_voice_slots,
    build_voice_map,
)


class FakeArchetype:
    host_name = "Alex"
    guest_name = "Dr."


def make_settings(**tts_kwargs) -> Settings:
    s = Settings()
    for k, v in tts_kwargs.items():
        setattr(s.tts, k, v)
    return s


def test_resolve_defaults_edge():
    s = make_settings()
    h, i, src = _resolve_voice_slots(s)
    assert h == "en-US-GuyNeural"
    assert i == "en-US-AriaNeural"
    assert src == "default"


def test_resolve_defaults_openai_compatible():
    s = make_settings(provider="openai_compatible")
    h, i, src = _resolve_voice_slots(s)
    assert h == "onyx"
    assert i == "nova"
    assert src == "default"


def test_resolve_config_both():
    s = make_settings(voices={"host": "en-US-GuyNeural", "interviewee": "en-US-JennyNeural"})
    h, i, src = _resolve_voice_slots(s)
    assert h == "en-US-GuyNeural"
    assert i == "en-US-JennyNeural"
    assert src == "config"


def test_resolve_config_partial_host_only():
    s = make_settings(voices={"host": "en-US-GuyNeural"})
    h, i, src = _resolve_voice_slots(s)
    assert h == "en-US-GuyNeural"
    assert i == "en-US-AriaNeural"
    assert src == "config"


def test_resolve_legacy_voice_warns():
    s = make_settings(voice="en-US-GuyNeural")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        h, i, src = _resolve_voice_slots(s)
    assert h == "en-US-GuyNeural"
    assert i == "en-US-GuyNeural"
    assert src == "legacy"
    assert any("deprecated" in str(warning.message).lower() for warning in w)


def test_resolve_equal_voices_warns():
    s = make_settings(voices={"host": "en-US-AriaNeural", "interviewee": "en-US-AriaNeural"})
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        h, i, src = _resolve_voice_slots(s)
    assert h == i
    assert src == "config"
    assert any("identical" in str(warning.message).lower() for warning in w)


def test_build_voice_map_default():
    s = make_settings()
    vm = build_voice_map(s, FakeArchetype())
    assert vm["Alex"] == "en-US-GuyNeural"
    assert vm["Dr."] == "en-US-AriaNeural"


def test_build_voice_map_config_override():
    s = make_settings(voices={"host": "en-US-GuyNeural", "interviewee": "en-US-JennyNeural"})
    vm = build_voice_map(s, FakeArchetype())
    assert vm["Alex"] == "en-US-GuyNeural"
    assert vm["Dr."] == "en-US-JennyNeural"


# ── Language-aware voice defaults ──────────────────────────────


class TestLanguageAwareDefaults:
    """TDD: resolve TTS voice defaults per language."""

    def test_default_edge_zh_CN_returns_chinese_voices(self):
        """No explicit voices + language zh-CN → Chinese edge defaults."""
        s = make_settings()
        h, i, src = _resolve_voice_slots(s, language="zh-CN")
        assert h == "zh-CN-YunxiNeural"
        assert i == "zh-CN-XiaoxiaoNeural"
        assert src == "default"

    def test_default_edge_en_returns_english_voices(self):
        """No explicit voices + language en → English edge defaults."""
        s = make_settings()
        h, i, src = _resolve_voice_slots(s, language="en")
        assert h == "en-US-GuyNeural"
        assert i == "en-US-AriaNeural"
        assert src == "default"

    def test_default_edge_unknown_language_falls_back_to_en(self):
        """Unsupported language → falls back to English edge defaults."""
        s = make_settings()
        h, i, src = _resolve_voice_slots(s, language="fr")
        assert h == "en-US-GuyNeural"
        assert i == "en-US-AriaNeural"
        assert src == "default"

    def test_explicit_voices_override_language_defaults_no_warning(self):
        """Explicit voice_map overrides language defaults, no mismatch warning."""
        s = make_settings(voices={"host": "zh-CN-YunxiNeural", "interviewee": "zh-CN-XiaoxiaoNeural"})
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            h, i, src = _resolve_voice_slots(s, language="zh-CN")
        assert h == "zh-CN-YunxiNeural"
        assert i == "zh-CN-XiaoxiaoNeural"
        assert src == "config"
        mismatch_warnings = [
            x for x in w if "zh-CN but TTS voice is English" in str(x.message)
        ]
        assert len(mismatch_warnings) == 0

    def test_zh_CN_language_with_english_voice_warns(self):
        """Language zh-CN but user explicitly set English voices → warning."""
        s = make_settings(voices={"host": "en-US-GuyNeural", "interviewee": "en-US-AriaNeural"})
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            h, i, src = _resolve_voice_slots(s, language="zh-CN")
        assert h == "en-US-GuyNeural"
        assert i == "en-US-AriaNeural"
        assert src == "config"
        mismatch_warnings = [
            x for x in w if "zh-CN but TTS voice is English" in str(x.message)
        ]
        assert len(mismatch_warnings) == 1

    def test_en_language_with_chinese_voice_no_warning(self):
        """Language en with Chinese voices — no warning (valid use case)."""
        s = make_settings(voices={"host": "zh-CN-YunxiNeural", "interviewee": "zh-CN-XiaoxiaoNeural"})
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            h, i, src = _resolve_voice_slots(s, language="en")
        assert h == "zh-CN-YunxiNeural"
        assert i == "zh-CN-XiaoxiaoNeural"
        assert src == "config"
        mismatch_warnings = [
            x for x in w if "zh-CN but TTS voice is English" in str(x.message)
        ]
        assert len(mismatch_warnings) == 0

    def test_openai_compatible_ignores_language_defaults(self):
        """OpenAI-compatible provider ignores language defaults (onyx/nova always)."""
        s = make_settings(provider="openai_compatible")
        h, i, src = _resolve_voice_slots(s, language="zh-CN")
        assert h == "onyx"
        assert i == "nova"
        assert src == "default"

    def test_build_voice_map_passes_language_through(self):
        """build_voice_map with language=zh-CN → Chinese voice map."""
        s = make_settings()
        vm = build_voice_map(s, FakeArchetype(), language="zh-CN")
        assert vm["Alex"] == "zh-CN-YunxiNeural"
        assert vm["Dr."] == "zh-CN-XiaoxiaoNeural"

    def test_default_edge_en_explicit_language_same_as_before(self):
        """Backward compat: _resolve_voice_slots defaults (no language arg) → English."""
        s = make_settings()
        h, i, src = _resolve_voice_slots(s)
        assert h == "en-US-GuyNeural"
        assert i == "en-US-AriaNeural"
        assert src == "default"

    def test_partial_config_with_zh_CN_fills_gap_from_language_defaults(self):
        """Host set explicitly, interviewee falls back to zh-CN default."""
        s = make_settings(voices={"host": "en-US-GuyNeural"})
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            h, i, src = _resolve_voice_slots(s, language="zh-CN")
        assert h == "en-US-GuyNeural"
        assert i == "zh-CN-XiaoxiaoNeural"
        assert src == "config"
        mismatch_warnings = [
            x for x in caught if "zh-CN but TTS voice is English" in str(x.message)
        ]
        assert len(mismatch_warnings) == 1
