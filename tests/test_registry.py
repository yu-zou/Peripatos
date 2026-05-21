"""Tests for registry.py — build_voice_map and _resolve_voice_slots."""

import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from peripatos_core.config import Settings  # pyright: ignore
from peripatos_core.registry import (  # pyright: ignore
    _resolve_voice_slots,
    build_voice_map,
)


class FakeArchetype:
    host_name = "Alex"
    guest_name = "Dr. Chen"


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
    assert vm["Dr. Chen"] == "en-US-AriaNeural"


def test_build_voice_map_config_override():
    s = make_settings(voices={"host": "en-US-GuyNeural", "interviewee": "en-US-JennyNeural"})
    vm = build_voice_map(s, FakeArchetype())
    assert vm["Alex"] == "en-US-GuyNeural"
    assert vm["Dr. Chen"] == "en-US-JennyNeural"
