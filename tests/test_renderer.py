"""Tests for audio renderer orchestrator."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from peripatos.voice.renderer import AudioRenderer
from peripatos.config import PeripatosConfig
from peripatos.models import (
    DialogueScript, DialogueTurn, SpeakerRole, PersonaType, 
    LanguageMode, PaperMetadata, SectionInfo, SectionType, AudioSegment
)
from pathlib import Path


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return PeripatosConfig(
        llm_provider="openai",
        llm_model="gpt-4o",
        tts_engine="openai",
        tts_voice_host="alloy",
        tts_voice_expert="onyx",
        persona="tutor",
        language="en",
        output_dir="./output",
        openai_api_key="test-key-123"
    )


@pytest.fixture
def mock_dialogue_script():
    """Create a mock dialogue script for testing."""
    metadata = PaperMetadata(
        title="Test Paper",
        authors=["Author One", "Author Two"],
        abstract="This is a test abstract.",
        source_path=Path("/test/paper.pdf"),
        sections=[
            SectionInfo(
                title="Introduction",
                content="Test content",
                section_type=SectionType.INTRODUCTION
            )
        ]
    )
    
    turns = [
        DialogueTurn(speaker=SpeakerRole.HOST, text="Welcome to the podcast.", section_ref="intro"),
        DialogueTurn(speaker=SpeakerRole.EXPERT, text="Thanks for having me.", section_ref="intro"),
        DialogueTurn(speaker=SpeakerRole.HOST, text="Let's discuss the paper.", section_ref="intro"),
    ]
    
    return DialogueScript(
        paper_metadata=metadata,
        turns=turns,
        persona_type=PersonaType.TUTOR,
        language_mode=LanguageMode.EN
    )


class TestAudioRenderer:
    """Test suite for AudioRenderer class."""

    def test_openai_engine_selected_when_available(self, mock_config, mock_dialogue_script):
        """Test that OpenAI engine is selected when API key is available."""
        with patch('peripatos.voice.renderer.OpenAITTSEngine') as MockOpenAI:
            mock_openai_instance = Mock()
            mock_openai_instance.is_available.return_value = True
            MockOpenAI.return_value = mock_openai_instance
            
            renderer = AudioRenderer(mock_config)
            
            # Verify OpenAI engine was selected
            assert renderer.active_engine_name == "openai"
            MockOpenAI.assert_called_once()

    def test_edge_tts_fallback_when_openai_unavailable(self, mock_config, mock_dialogue_script):
        """Test that edge-tts is used as fallback when OpenAI key is missing."""
        # Configure for OpenAI but with no API key
        config_no_key = PeripatosConfig(
            llm_provider="openai",
            llm_model="gpt-4o",
            tts_engine="openai",
            tts_voice_host="alloy",
            tts_voice_expert="onyx",
            persona="tutor",
            language="en",
            output_dir="./output",
            openai_api_key=None  # No API key
        )
        
        with patch('peripatos.voice.renderer.OpenAITTSEngine') as MockOpenAI, \
             patch('peripatos.voice.renderer.EdgeTTSEngine') as MockEdge:
            
            mock_openai_instance = Mock()
            mock_openai_instance.is_available.return_value = False
            MockOpenAI.return_value = mock_openai_instance
            
            mock_edge_instance = Mock()
            mock_edge_instance.is_available.return_value = True
            MockEdge.return_value = mock_edge_instance
            
            renderer = AudioRenderer(config_no_key)
            
            # Verify edge-tts was selected as fallback
            assert renderer.active_engine_name == "edge-tts"
            MockEdge.assert_called_once()

    def test_host_and_expert_get_different_voices(self, mock_config, mock_dialogue_script):
        """Test that HOST and EXPERT speakers get different voices."""
        with patch('peripatos.voice.renderer.OpenAITTSEngine') as MockOpenAI:
            mock_openai_instance = Mock()
            mock_openai_instance.is_available.return_value = True
            mock_openai_instance.synthesize.return_value = b"fake_audio_data"
            MockOpenAI.return_value = mock_openai_instance
            
            renderer = AudioRenderer(mock_config)
            segments = renderer.render(mock_dialogue_script)
            
            # Extract the voices used for each call
            calls = mock_openai_instance.synthesize.call_args_list
            
            # Should have 3 calls (3 turns)
            assert len(calls) >= 3
            
            # Extract voice parameter from calls
            # First call should be for HOST
            host_voice = calls[0][1]['voice'] if 'voice' in calls[0][1] else calls[0][0][1]
            # Second call should be for EXPERT
            expert_voice = calls[1][1]['voice'] if 'voice' in calls[1][1] else calls[1][0][1]
            
            # Verify voices are different
            assert host_voice != expert_voice
            assert host_voice == mock_config.tts_voice_host
            assert expert_voice == mock_config.tts_voice_expert

    def test_silence_padding_inserted_between_turns(self, mock_config, mock_dialogue_script):
        """Test that 300ms silence padding is inserted between turns."""
        with patch('peripatos.voice.renderer.OpenAITTSEngine') as MockOpenAI, \
             patch('peripatos.voice.renderer.PydubAudioSegment') as MockPydubAudioSegment:
            
            mock_openai_instance = Mock()
            mock_openai_instance.is_available.return_value = True
            mock_openai_instance.synthesize.return_value = b"fake_audio_data"
            MockOpenAI.return_value = mock_openai_instance
            
            # Mock pydub AudioSegment
            mock_audio_seg = Mock()
            # Make __add__ return a new mock to chain operations
            mock_audio_seg.__add__ = Mock(return_value=mock_audio_seg)
            mock_audio_seg.__len__ = Mock(return_value=1500)  # 1.5 seconds in ms
            mock_export_context = Mock()
            mock_export_result = Mock()
            mock_export_result.read = Mock(return_value=b"exported")
            mock_export_context.__enter__ = Mock(return_value=mock_export_result)
            mock_export_context.__exit__ = Mock(return_value=None)
            mock_audio_seg.export = Mock(return_value=mock_export_context)
            
            MockPydubAudioSegment.from_mp3 = Mock(return_value=mock_audio_seg)
            MockPydubAudioSegment.silent = Mock(return_value=mock_audio_seg)
            
            renderer = AudioRenderer(mock_config)
            segments = renderer.render(mock_dialogue_script)
            
            # Now test the add_silence_padding method separately
            merged_audio = renderer.add_silence_padding(segments)
            
            # Verify silent() was called once with duration=300ms
            MockPydubAudioSegment.silent.assert_called_once_with(duration=300)
            
            # Verify from_mp3 was called for each segment in both render() and add_silence_padding()
            # 3 calls during render (for duration calculation)
            # 3 calls during add_silence_padding (for merging)
            assert MockPydubAudioSegment.from_mp3.call_count == 6
            
            # Verify __add__ was called (silence is added between segments)
            # With 3 segments: combined = seg1 + silence + seg2 + silence + seg3
            # This results in: seg1.__add__(silence), then temp1.__add__(seg2), etc.
            # At minimum should have 4 additions (2 for silence, 2 for segments)
            assert mock_audio_seg.__add__.call_count >= 4
            
            # Verify export was called to generate final output
            assert mock_audio_seg.export.call_count >= 1

    def test_render_produces_audiosegment_list_matching_script_length(self, mock_config, mock_dialogue_script):
        """Test that render() produces AudioSegment list matching DialogueScript length."""
        with patch('peripatos.voice.renderer.OpenAITTSEngine') as MockOpenAI:
            mock_openai_instance = Mock()
            mock_openai_instance.is_available.return_value = True
            mock_openai_instance.synthesize.return_value = b"fake_audio_data"
            MockOpenAI.return_value = mock_openai_instance
            
            renderer = AudioRenderer(mock_config)
            segments = renderer.render(mock_dialogue_script)
            
            # Should return list of AudioSegment
            assert isinstance(segments, list)
            
            # Should have same number of segments as dialogue turns
            assert len(segments) == len(mock_dialogue_script.turns)
            
            # Each segment should be an AudioSegment
            for seg in segments:
                assert hasattr(seg, 'speaker')
                assert hasattr(seg, 'audio_bytes')
                assert hasattr(seg, 'duration_seconds')
                assert hasattr(seg, 'text')

    def test_edge_tts_uses_correct_voice_mapping(self, mock_dialogue_script):
        """Test that edge-tts engine uses correct voice mapping for host/expert."""
        config_edge = PeripatosConfig(
            llm_provider="openai",
            llm_model="gpt-4o",
            tts_engine="edge-tts",
            tts_voice_host="en-US-AriaNeural",
            tts_voice_expert="en-US-GuyNeural",
            persona="tutor",
            language="en",
            output_dir="./output",
            openai_api_key=None
        )
        
        with patch('peripatos.voice.renderer.EdgeTTSEngine') as MockEdge:
            mock_edge_instance = Mock()
            mock_edge_instance.is_available.return_value = True
            mock_edge_instance.synthesize_sync.return_value = b"fake_edge_audio"
            MockEdge.return_value = mock_edge_instance
            
            renderer = AudioRenderer(config_edge)
            segments = renderer.render(mock_dialogue_script)
            
            # Verify synthesize_sync was called with correct voices
            calls = mock_edge_instance.synthesize_sync.call_args_list
            
            # First call (HOST)
            host_call_voice = calls[0][1]['voice'] if 'voice' in calls[0][1] else calls[0][0][1]
            assert host_call_voice == config_edge.tts_voice_host
            
            # Second call (EXPERT)
            expert_call_voice = calls[1][1]['voice'] if 'voice' in calls[1][1] else calls[1][0][1]
            assert expert_call_voice == config_edge.tts_voice_expert

    def test_progress_callback_is_called(self, mock_config, mock_dialogue_script):
        """Test that progress callback is invoked during rendering."""
        with patch('peripatos.voice.renderer.OpenAITTSEngine') as MockOpenAI:
            mock_openai_instance = Mock()
            mock_openai_instance.is_available.return_value = True
            mock_openai_instance.synthesize.return_value = b"fake_audio_data"
            MockOpenAI.return_value = mock_openai_instance
            
            # Create a mock progress callback
            progress_callback = Mock()
            
            renderer = AudioRenderer(mock_config)
            segments = renderer.render(mock_dialogue_script, progress_callback=progress_callback)
            
            # Callback should be called for each turn
            assert progress_callback.call_count == len(mock_dialogue_script.turns)
            
            # Verify callback was called with turn index and total
            for i in range(len(mock_dialogue_script.turns)):
                progress_callback.assert_any_call(i + 1, len(mock_dialogue_script.turns))
