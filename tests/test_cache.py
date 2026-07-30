"""Tests for cache layer."""
import json
from pathlib import Path
from unittest.mock import Mock

from peripatos_core.cache import CacheManager, CachedTTSProvider
from peripatos_core.types import (
    ArchetypeId,
    Chapter,
    DialogueScript,
    DialogueTurn,
)


class TestCacheManagerAudio:
    def test_audio_key_is_deterministic(self, tmp_path):
        mgr = CacheManager(tmp_path)
        k1 = mgr.audio_key("edge", "voiceA", "hello world")
        k2 = mgr.audio_key("edge", "voiceA", "hello world")
        assert k1 == k2

    def test_audio_key_changes_with_provider(self, tmp_path):
        mgr = CacheManager(tmp_path)
        k1 = mgr.audio_key("edge", "v", "hello")
        k2 = mgr.audio_key("elevenlabs", "v", "hello")
        assert k1 != k2

    def test_audio_key_changes_with_voice(self, tmp_path):
        mgr = CacheManager(tmp_path)
        k1 = mgr.audio_key("edge", "voiceA", "hello")
        k2 = mgr.audio_key("edge", "voiceB", "hello")
        assert k1 != k2

    def test_audio_key_changes_with_text(self, tmp_path):
        mgr = CacheManager(tmp_path)
        k1 = mgr.audio_key("edge", "v", "hello")
        k2 = mgr.audio_key("edge", "v", "goodbye")
        assert k1 != k2

    def test_audio_put_and_get(self, tmp_path):
        mgr = CacheManager(tmp_path)
        src = tmp_path / "src.mp3"
        src.write_bytes(b"fake mp3 data")
        key = mgr.audio_key("edge", "voiceA", "hello world")

        mgr.audio_put(key, src)
        result = mgr.audio_get(key)
        assert result is not None
        assert result.read_bytes() == b"fake mp3 data"

    def test_audio_get_disabled(self, tmp_path):
        mgr = CacheManager(tmp_path, audio_enabled=False)
        key = mgr.audio_key("edge", "v", "hello")
        src = tmp_path / "src.mp3"
        src.write_bytes(b"data")
        mgr.audio_put(key, src)
        assert mgr.audio_get(key) is None

    def test_audio_get_nonexistent(self, tmp_path):
        mgr = CacheManager(tmp_path)
        assert mgr.audio_get("nonexistent123") is None


class TestCacheManagerDialogue:
    def _make_script(self, title="Test Paper") -> DialogueScript:
        return DialogueScript(
            title=title,
            chapters=[
                Chapter(
                    title="Intro",
                    turns=[
                        DialogueTurn(speaker="Host", text="Hello", archetype=ArchetypeId.PEER),
                        DialogueTurn(speaker="Expert", text="Hi", archetype=ArchetypeId.PEER),
                    ],
                )
            ],
            intro_turns=[],
            outro_turns=[],
        )

    def test_dialogue_key_is_deterministic(self, tmp_path):
        mgr = CacheManager(tmp_path)
        content = "some paper content"
        k1 = mgr.dialogue_key("gpt-4", "peer", "en", content)
        k2 = mgr.dialogue_key("gpt-4", "peer", "en", content)
        assert k1 == k2

    def test_dialogue_key_changes_with_model(self, tmp_path):
        mgr = CacheManager(tmp_path)
        k1 = mgr.dialogue_key("gpt-4", "peer", "en", "content")
        k2 = mgr.dialogue_key("claude", "peer", "en", "content")
        assert k1 != k2

    def test_dialogue_key_changes_with_prompt_version(self, tmp_path):
        mgr = CacheManager(tmp_path)
        k1 = mgr.dialogue_key("gpt-4", "peer", "en", "content", prompt_version="aaaa")
        k2 = mgr.dialogue_key("gpt-4", "peer", "en", "content", prompt_version="bbbb")
        assert k1 != k2

    def test_dialogue_key_default_version_backward_compatible(self, tmp_path):
        mgr = CacheManager(tmp_path)
        # 4-positional-arg call (existing call style) must still work
        k = mgr.dialogue_key("gpt-4", "peer", "en", "content")
        assert isinstance(k, str) and len(k) == 16

    def test_dialogue_put_and_get_roundtrip(self, tmp_path):
        mgr = CacheManager(tmp_path)
        script = self._make_script("My Paper")
        key = mgr.dialogue_key("gpt-4", "peer", "en", "paper text here")

        mgr.dialogue_put(key, script)
        loaded = mgr.dialogue_get(key)
        assert loaded is not None
        assert loaded.title == "My Paper"
        assert len(loaded.chapters) == 1
        assert len(loaded.chapters[0].turns) == 2
        assert loaded.chapters[0].turns[0].speaker == "Host"
        assert loaded.chapters[0].turns[1].text == "Hi"

    def test_dialogue_get_disabled(self, tmp_path):
        mgr = CacheManager(tmp_path, dialogue_enabled=False)
        script = self._make_script()
        key = mgr.dialogue_key("gpt-4", "peer", "en", "text")
        mgr.dialogue_put(key, script)
        assert mgr.dialogue_get(key) is None

    def test_dialogue_get_nonexistent(self, tmp_path):
        mgr = CacheManager(tmp_path)
        assert mgr.dialogue_get("nonexistent123") is None


class TestCachedTTSProvider:
    def test_cache_hit_returns_cached_path(self, tmp_path):
        delegate = Mock()
        delegate.synthesize.return_value = tmp_path / "fresh.mp3"

        src = tmp_path / "src.mp3"
        src.write_bytes(b"cached data")

        mgr = CacheManager(tmp_path)
        provider = CachedTTSProvider(delegate, mgr, provider_name="edge")

        # Pre-populate cache
        key = mgr.audio_key("edge", "v", "hello world")
        mgr.audio_put(key, src)

        result = provider.synthesize("hello world", speaker_voice="v")
        assert result is not None
        assert result.read_bytes() == b"cached data"
        delegate.synthesize.assert_not_called()

    def test_cache_miss_delegates(self, tmp_path):
        fresh = tmp_path / "fresh.mp3"
        fresh.write_bytes(b"fresh data")

        delegate = Mock()
        delegate.synthesize.return_value = fresh

        mgr = CacheManager(tmp_path)
        provider = CachedTTSProvider(delegate, mgr, provider_name="edge")

        result = provider.synthesize("hello world", speaker_voice="v")
        assert result is not None
        delegate.synthesize.assert_called_once_with(
            "hello world", speaker_voice="v"
        )
        # After miss, the result should be cached
        key = mgr.audio_key("edge", "v", "hello world")
        assert mgr.audio_get(key) is not None
