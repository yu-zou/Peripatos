"""Tests for edge-tts fallback engine."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from peripatos.voice.edge_tts_engine import EdgeTTSEngine, TTSError


class TestEdgeTTSEngine:
    """Test suite for EdgeTTSEngine class."""

    def test_is_available_always_returns_true(self):
        """Test that is_available() always returns True (no API key needed)."""
        engine = EdgeTTSEngine()
        assert engine.is_available() is True

    def test_get_voices_english_language(self):
        """Test get_voices() returns correct English host/expert voices."""
        engine = EdgeTTSEngine()
        voices = engine.get_voices("en")
        
        assert "host" in voices
        assert "expert" in voices
        assert voices["host"] == "en-US-AriaNeural"
        assert voices["expert"] == "en-US-GuyNeural"

    def test_get_voices_chinese_language(self):
        """Test get_voices() returns correct Chinese host/expert voices."""
        engine = EdgeTTSEngine()
        voices = engine.get_voices("zh")
        
        assert "host" in voices
        assert "expert" in voices
        assert voices["host"] == "zh-CN-XiaoxiaoNeural"
        assert voices["expert"] == "zh-CN-YunxiNeural"

    def test_get_voices_returns_distinct_voices(self):
        """Test that host and expert voices are distinct."""
        engine = EdgeTTSEngine()
        
        en_voices = engine.get_voices("en")
        zh_voices = engine.get_voices("zh")
        
        # English voices should be different
        assert en_voices["host"] != en_voices["expert"]
        
        # Chinese voices should be different
        assert zh_voices["host"] != zh_voices["expert"]
        
        # English and Chinese voices should be different
        assert en_voices["host"] != zh_voices["host"]

    @pytest.mark.asyncio
    async def test_synthesize_returns_audio_bytes(self):
        """Test that synthesize() returns audio bytes when given valid voice."""
        engine = EdgeTTSEngine()
        
        # Mock edge_tts.Communicate
        mock_communicate = AsyncMock()
        mock_chunk_audio = {"type": "audio", "data": b"mock_audio_data"}
        mock_chunk_other = {"type": "token", "data": "token_data"}
        
        async def mock_stream():
            yield mock_chunk_other
            yield mock_chunk_audio
            yield mock_chunk_other
        
        mock_communicate.stream = mock_stream
        
        with patch("peripatos.voice.edge_tts_engine.edge_tts.Communicate", return_value=mock_communicate):
            result = await engine.synthesize("Hello world", "en-US-AriaNeural")
            
            # Should return only audio data bytes, not other chunks
            assert result == b"mock_audio_data"
            assert isinstance(result, bytes)

    @pytest.mark.asyncio
    async def test_synthesize_concatenates_multiple_audio_chunks(self):
        """Test that synthesize() concatenates multiple audio chunks."""
        engine = EdgeTTSEngine()
        
        mock_communicate = AsyncMock()
        
        async def mock_stream():
            yield {"type": "audio", "data": b"chunk1"}
            yield {"type": "audio", "data": b"chunk2"}
            yield {"type": "audio", "data": b"chunk3"}
        
        mock_communicate.stream = mock_stream
        
        with patch("peripatos.voice.edge_tts_engine.edge_tts.Communicate", return_value=mock_communicate):
            result = await engine.synthesize("Hello world", "en-US-AriaNeural")
            
            assert result == b"chunk1chunk2chunk3"
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_synthesize_with_invalid_voice_raises_error(self):
        """Test that synthesize() handles invalid voice names gracefully."""
        engine = EdgeTTSEngine()
        
        mock_communicate = AsyncMock()
        mock_communicate.stream = AsyncMock(side_effect=ValueError("Invalid voice"))
        
        with patch("peripatos.voice.edge_tts_engine.edge_tts.Communicate", return_value=mock_communicate):
            with pytest.raises(TTSError):
                await engine.synthesize("Hello world", "invalid-voice-name")

    def test_synthesize_sync_wrapper(self):
        """Test that synthesize_sync() wraps async method correctly."""
        engine = EdgeTTSEngine()
        
        mock_communicate = AsyncMock()
        
        async def mock_stream():
            yield {"type": "audio", "data": b"test_audio"}
        
        mock_communicate.stream = mock_stream
        
        with patch("peripatos.voice.edge_tts_engine.edge_tts.Communicate", return_value=mock_communicate):
            result = engine.synthesize_sync("Hello world", "en-US-AriaNeural")
            
            assert result == b"test_audio"
            assert isinstance(result, bytes)

    def test_tts_error_exception_exists(self):
        """Test that TTSError exception can be raised."""
        with pytest.raises(TTSError):
            raise TTSError("Test error message")
