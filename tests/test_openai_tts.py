"""Tests for OpenAI TTS engine."""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from peripatos.voice.openai_tts import OpenAITTSEngine, TTSError


class TestOpenAITTSEngine:
    """Test suite for OpenAITTSEngine."""

    def test_chunk_text_respects_sentence_boundaries(self):
        """Test that text chunking splits at sentence boundaries."""
        engine = OpenAITTSEngine(api_key="test-key")
        
        # Create text with multiple sentences
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        
        chunks = engine._chunk_text(text)
        
        # Each sentence should end with a period
        for chunk in chunks:
            # Remove trailing space if present
            chunk_stripped = chunk.rstrip()
            if chunk_stripped:
                # Should end with sentence boundary
                assert chunk_stripped[-1] in {'.', '!', '?'}

    def test_chunk_text_never_exceeds_limit(self):
        """Test that chunks never exceed 4096 character limit."""
        engine = OpenAITTSEngine(api_key="test-key")
        
        # Create very long text with sentences
        long_sentence = "This is a sentence that will be repeated many times. "
        text = long_sentence * 100  # ~5000 chars
        
        chunks = engine._chunk_text(text)
        
        # Verify no chunk exceeds limit
        for chunk in chunks:
            assert len(chunk) <= 4096, f"Chunk length {len(chunk)} exceeds limit"

    def test_chunk_text_splits_at_clause_boundaries_for_long_sentences(self):
        """Test that very long sentences are split at clause boundaries."""
        engine = OpenAITTSEngine(api_key="test-key")
        
        # Create a single sentence longer than 4096 chars with commas
        clause = "this is a very long clause with many words, "
        # Make a sentence > 4096 chars
        text = clause * 100 + "and this is the end."
        
        chunks = engine._chunk_text(text)
        
        # Should be split into multiple chunks
        assert len(chunks) > 1
        
        # Verify no chunk exceeds limit
        for chunk in chunks:
            assert len(chunk) <= 4096

    def test_is_available_returns_false_when_api_key_missing(self):
        """Test that is_available returns False when API key is missing."""
        # Test with None
        engine = OpenAITTSEngine(api_key=None)
        assert engine.is_available() is False
        
        # Test with empty string
        engine = OpenAITTSEngine(api_key="")
        assert engine.is_available() is False

    def test_is_available_returns_true_when_api_key_present(self):
        """Test that is_available returns True when API key is present."""
        engine = OpenAITTSEngine(api_key="test-key")
        assert engine.is_available() is True

    @patch('peripatos.voice.openai_tts.OpenAI')
    def test_synthesize_returns_audio_bytes(self, mock_openai):
        """Test that synthesize returns audio bytes from mocked API."""
        # Setup mock
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.read.return_value = b"fake-audio-data"
        mock_client.audio.speech.create.return_value = mock_response
        
        # Create engine and synthesize
        engine = OpenAITTSEngine(api_key="test-key")
        result = engine.synthesize("Hello world.", voice="alloy")
        
        # Verify
        assert result == b"fake-audio-data"
        mock_client.audio.speech.create.assert_called_once_with(
            model="tts-1",
            voice="alloy",
            input="Hello world."
        )

    @patch('peripatos.voice.openai_tts.OpenAI')
    def test_synthesize_with_different_voices(self, mock_openai):
        """Test that different voices are passed to the API."""
        # Setup mock
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.read.return_value = b"audio"
        mock_client.audio.speech.create.return_value = mock_response
        
        engine = OpenAITTSEngine(api_key="test-key")
        
        # Test with "alloy" voice
        engine.synthesize("Host speaking.", voice="alloy")
        assert mock_client.audio.speech.create.call_args[1]["voice"] == "alloy"
        
        # Test with "onyx" voice
        engine.synthesize("Expert speaking.", voice="onyx")
        assert mock_client.audio.speech.create.call_args[1]["voice"] == "onyx"

    @patch('peripatos.voice.openai_tts.OpenAI')
    def test_synthesize_concatenates_chunks(self, mock_openai):
        """Test that multiple chunks are concatenated properly."""
        # Setup mock
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Mock responses for multiple chunks
        call_count = [0]
        def mock_create(**kwargs):
            response = Mock()
            response.read.return_value = f"audio-chunk-{call_count[0]}".encode()
            call_count[0] += 1
            return response
        
        mock_client.audio.speech.create.side_effect = mock_create
        
        # Create text that will be split into chunks
        long_sentence = "This is a sentence. "
        text = long_sentence * 250  # Should create multiple chunks
        
        engine = OpenAITTSEngine(api_key="test-key")
        result = engine.synthesize(text, voice="alloy")
        
        # Should have made multiple API calls
        assert mock_client.audio.speech.create.call_count > 1
        
        # Result should be concatenated
        assert b"audio-chunk-0" in result
        assert b"audio-chunk-1" in result

    def test_synthesize_raises_error_when_api_key_missing(self):
        """Test that synthesize raises TTSError when API key is missing."""
        engine = OpenAITTSEngine(api_key=None)
        
        with pytest.raises(TTSError, match="OpenAI API key not available"):
            engine.synthesize("Test text", voice="alloy")

    @patch('peripatos.voice.openai_tts.OpenAI')
    def test_synthesize_handles_api_errors(self, mock_openai):
        """Test that API errors are caught and wrapped in TTSError."""
        # Setup mock to raise error
        mock_client = Mock()
        mock_openai.return_value = mock_client
        mock_client.audio.speech.create.side_effect = Exception("API Error")
        
        engine = OpenAITTSEngine(api_key="test-key")
        
        with pytest.raises(TTSError, match="TTS synthesis failed"):
            engine.synthesize("Test text", voice="alloy")

    def test_chunk_text_handles_empty_string(self):
        """Test that empty string returns empty list."""
        engine = OpenAITTSEngine(api_key="test-key")
        
        chunks = engine._chunk_text("")
        
        assert chunks == []

    def test_chunk_text_preserves_short_text(self):
        """Test that text shorter than limit is returned as-is."""
        engine = OpenAITTSEngine(api_key="test-key")
        
        text = "Short text."
        chunks = engine._chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0] == text

    @patch('peripatos.voice.openai_tts.OpenAI')
    def test_synthesize_uses_default_model(self, mock_openai):
        """Test that tts-1 model is used by default."""
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        mock_response = Mock()
        mock_response.read.return_value = b"audio"
        mock_client.audio.speech.create.return_value = mock_response
        
        engine = OpenAITTSEngine(api_key="test-key")
        engine.synthesize("Test", voice="alloy")
        
        # Verify tts-1 model is used (not tts-1-hd)
        assert mock_client.audio.speech.create.call_args[1]["model"] == "tts-1"

    def test_initialization_from_env_variable(self):
        """Test that engine can be initialized from environment variable."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"}):
            engine = OpenAITTSEngine()
            assert engine.is_available() is True

    def test_chunk_text_handles_mixed_punctuation(self):
        """Test chunking with mixed punctuation (periods, questions, exclamations)."""
        engine = OpenAITTSEngine(api_key="test-key")
        
        text = "First sentence. Is this a question? This is exciting! Another sentence."
        chunks = engine._chunk_text(text)
        
        # Should preserve all punctuation
        full_text = "".join(chunks)
        assert "?" in full_text
        assert "!" in full_text
        assert "." in full_text
