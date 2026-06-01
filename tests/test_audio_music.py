"""Tests for intro/outro music injection."""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from peripatos_core.audio import AudioRenderer
from peripatos_core.exceptions import AudioError


class TestLoadMusic:
    """Test _load_music loads bundled MP3s and raises on missing files."""

    def test_load_music_raises_on_missing_file(self):
        renderer = AudioRenderer(tts=MagicMock())
        with pytest.raises(AudioError, match="Music file not found"):
            renderer._load_music("nonexistent.mp3")

    def test_load_music_blocks_directory_traversal(self):
        renderer = AudioRenderer(tts=MagicMock())
        with pytest.raises(AudioError, match="Music file must be inside"):
            renderer._load_music("../evil.mp3")

    @patch("peripatos_core.audio.PydubAudioSegment")
    def test_load_music_returns_segment(self, mock_segment):
        mock_segment.from_mp3.return_value = MagicMock()
        renderer = AudioRenderer(tts=MagicMock())
        result = renderer._load_music("intro.mp3")
        assert result is not None
        mock_segment.from_mp3.assert_called_once()
