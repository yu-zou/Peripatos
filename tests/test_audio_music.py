"""Tests for _load_music: loading bundled MP3s and error handling."""
import pytest
from unittest.mock import patch, MagicMock
from peripatos_core.audio import AudioRenderer
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
