"""Tests for music loading, mixing, and error handling."""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from pydub import AudioSegment as PydubAudioSegment
from peripatos_core.audio import AudioRenderer, _AUDIO_DIR
from peripatos_core.exceptions import AudioError


class TestLoadMusic:
    """Test _load_music loads bundled MP3s and raises on missing/corrupt files."""

    def test_load_music_raises_on_missing_file(self):
        renderer = AudioRenderer(tts=MagicMock())
        with pytest.raises(AudioError, match="Music file not found"):
            renderer._load_music("nonexistent.mp3")

    def test_load_music_blocks_directory_traversal(self):
        renderer = AudioRenderer(tts=MagicMock())
        with pytest.raises(AudioError, match="Music file must be inside"):
            renderer._load_music("../evil.mp3")

    @patch("peripatos_core.audio.PydubAudioSegment")
    def test_load_music_calls_from_mp3_with_correct_path(self, mock_segment):
        mock_segment.from_mp3.return_value = MagicMock()
        renderer = AudioRenderer(tts=MagicMock())
        renderer._load_music("intro.mp3")
        call_args = mock_segment.from_mp3.call_args[0][0]
        assert "intro.mp3" in call_args
        mock_segment.from_mp3.assert_called_once()

    @patch("peripatos_core.audio.PydubAudioSegment")
    def test_load_music_raises_on_corrupt_file(self, mock_segment):
        mock_segment.from_mp3.side_effect = RuntimeError("corrupt mp3")
        renderer = AudioRenderer(tts=MagicMock())
        with pytest.raises(AudioError, match="Failed to load music file"):
            renderer._load_music("intro.mp3")

    def test_load_bundled_intro_mp3_real(self):
        """Verify the bundled intro.mp3 can be loaded by pydub."""
        renderer = AudioRenderer(tts=MagicMock())
        segment = renderer._load_music("intro.mp3")
        assert isinstance(segment, PydubAudioSegment)
        assert len(segment) > 0

    def test_load_bundled_outro_mp3_real(self):
        """Verify the bundled outro.mp3 can be loaded by pydub."""
        renderer = AudioRenderer(tts=MagicMock())
        segment = renderer._load_music("outro.mp3")
        assert isinstance(segment, PydubAudioSegment)
        assert len(segment) > 0


class TestMixMusic:
    """Test _mix_music prepends intro and appends outro with correct offsets."""

    def test_mix_music_returns_intro_offset(self):
        """_mix_music returns the correct intro duration as offset."""
        renderer = AudioRenderer(tts=MagicMock())
        dialogue = PydubAudioSegment.silent(duration=1000, frame_rate=44100)
        mixed, intro_offset_ms = renderer._mix_music(dialogue)
        # Intro music is 2000ms silent placeholder
        assert intro_offset_ms == 2000

    def test_mix_music_total_duration_includes_intro_and_outro(self):
        """Total duration = intro + dialogue + outro."""
        renderer = AudioRenderer(tts=MagicMock())
        dialogue_duration = 1000
        dialogue = PydubAudioSegment.silent(duration=dialogue_duration, frame_rate=44100)
        mixed, _ = renderer._mix_music(dialogue)
        # intro (2000ms) + dialogue (1000ms) + outro (2000ms) = 5000ms
        expected_total = 2000 + dialogue_duration + 2000
        assert len(mixed) == expected_total
