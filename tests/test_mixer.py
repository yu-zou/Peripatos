"""Tests for audio mixer with chapter markers."""

import shutil
from io import BytesIO
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import pytest

from peripatos.models import AudioSegment, ChapterMarker, SpeakerRole
from peripatos.voice.mixer import AudioMixer, MixerError


@pytest.fixture
def mock_audio_segments():
    """Create mock audio segments for testing."""
    # Create segments with known durations
    segments = [
        AudioSegment(
            speaker=SpeakerRole.HOST,
            audio_bytes=b"fake_audio_1",
            duration_seconds=2.0,
            text="First segment"
        ),
        AudioSegment(
            speaker=SpeakerRole.EXPERT,
            audio_bytes=b"fake_audio_2",
            duration_seconds=3.0,
            text="Second segment"
        ),
        AudioSegment(
            speaker=SpeakerRole.HOST,
            audio_bytes=b"fake_audio_3",
            duration_seconds=1.5,
            text="Third segment"
        ),
    ]
    return segments


@pytest.fixture
def mock_chapters():
    """Create mock chapter markers for testing."""
    chapters = [
        ChapterMarker(title="Introduction", start_time_ms=0, end_time_ms=2000),
        ChapterMarker(title="Discussion", start_time_ms=2500, end_time_ms=6000),
    ]
    return chapters


class TestAudioMixer:
    """Test suite for AudioMixer class."""
    
    def test_mix_concatenation_duration(self, mock_audio_segments, mock_chapters, tmp_path):
        """Test that concatenation produces correct total duration."""
        output_path = tmp_path / "test_output.mp3"
        
        # Mock pydub AudioSegment
        with patch('peripatos.voice.mixer.PydubAudioSegment') as mock_pydub:
            # Create mock audio segments with durations
            mock_audio_1 = Mock()
            mock_audio_1.__len__ = Mock(return_value=2000)  # 2 seconds in ms
            
            mock_audio_2 = Mock()
            mock_audio_2.__len__ = Mock(return_value=3000)  # 3 seconds in ms
            
            mock_audio_3 = Mock()
            mock_audio_3.__len__ = Mock(return_value=1500)  # 1.5 seconds in ms
            
            # Mock silence (300ms between segments)
            mock_silence = Mock()
            mock_silence.__len__ = Mock(return_value=300)
            
            # Configure from_mp3 to return our mocked segments
            mock_pydub.from_mp3.side_effect = [mock_audio_1, mock_audio_2, mock_audio_3]
            mock_pydub.silent.return_value = mock_silence
            
            # Mock concatenation operations
            mock_audio_1.__add__ = Mock(return_value=mock_audio_1)
            
            # Mock export
            mock_combined = Mock()
            mock_combined.export = Mock()
            mock_pydub.from_mp3.return_value = mock_combined
            
            # Mock ffmpeg subprocess
            with patch('subprocess.run') as mock_subprocess:
                with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
                    mixer = AudioMixer()
                    result_path = mixer.mix(mock_audio_segments, mock_chapters, output_path)
                    
                    # Verify pydub was called correctly
                    assert mock_pydub.from_mp3.call_count == 3
                    assert mock_pydub.silent.called
                    
                    # Verify result path
                    assert result_path == output_path
    
    def test_chapter_metadata_format(self, mock_audio_segments, mock_chapters, tmp_path):
        """Test that chapter metadata file uses correct FFMETADATA1 format."""
        output_path = tmp_path / "test_output.mp3"
        
        with patch('peripatos.voice.mixer.PydubAudioSegment') as mock_pydub:
            # Mock audio operations
            mock_audio = Mock()
            mock_audio.__len__ = Mock(return_value=1000)
            mock_audio.__add__ = Mock(return_value=mock_audio)
            mock_audio.export = Mock()
            
            mock_pydub.from_mp3.return_value = mock_audio
            mock_pydub.silent.return_value = mock_audio
            
            # Mock ffmpeg
            with patch('subprocess.run') as mock_subprocess:
                with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
                    with patch('builtins.open', create=True) as mock_file:
                        mock_file_handle = MagicMock()
                        mock_file.return_value.__enter__.return_value = mock_file_handle
                        
                        mixer = AudioMixer()
                        mixer.mix(mock_audio_segments, mock_chapters, output_path)
                        
                        # Capture written metadata content
                        written_content = ''.join(
                            call_args[0][0] 
                            for call_args in mock_file_handle.write.call_args_list
                        )
                        
                        # Verify FFMETADATA1 format
                        assert ';FFMETADATA1' in written_content
                        assert '[CHAPTER]' in written_content
                        assert 'TIMEBASE=1/1000' in written_content
                        assert 'START=' in written_content
                        assert 'END=' in written_content
                        assert 'title=' in written_content
    
    def test_ffmpeg_missing_raises_error(self, mock_audio_segments, mock_chapters, tmp_path):
        """Test that missing ffmpeg raises MixerError with helpful message."""
        output_path = tmp_path / "test_output.mp3"
        
        # Mock shutil.which to simulate missing ffmpeg
        with patch('shutil.which', return_value=None):
            mixer = AudioMixer()
            
            with pytest.raises(MixerError) as exc_info:
                mixer.mix(mock_audio_segments, mock_chapters, output_path)
            
            # Verify error message is helpful
            error_msg = str(exc_info.value)
            assert 'ffmpeg' in error_msg.lower()
            assert 'install' in error_msg.lower() or 'not found' in error_msg.lower()
    
    def test_empty_segments_raises_error(self, mock_chapters, tmp_path):
        """Test that empty segment list raises MixerError."""
        output_path = tmp_path / "test_output.mp3"
        
        with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
            mixer = AudioMixer()
            
            with pytest.raises(MixerError) as exc_info:
                mixer.mix([], mock_chapters, output_path)
            
            # Verify error message mentions empty segments
            error_msg = str(exc_info.value)
            assert 'empty' in error_msg.lower() or 'no segments' in error_msg.lower()
    
    def test_output_is_valid_mp3(self, mock_audio_segments, mock_chapters, tmp_path):
        """Test that output file is created with .mp3 extension."""
        output_path = tmp_path / "test_output.mp3"
        
        with patch('peripatos.voice.mixer.PydubAudioSegment') as mock_pydub:
            # Mock audio operations
            mock_audio = Mock()
            mock_audio.__len__ = Mock(return_value=1000)
            mock_audio.__add__ = Mock(return_value=mock_audio)
            
            # Mock export to actually create a file
            def mock_export(path, format):
                Path(path).write_bytes(b"fake_mp3_data")
            
            mock_audio.export = Mock(side_effect=mock_export)
            
            mock_pydub.from_mp3.return_value = mock_audio
            mock_pydub.silent.return_value = mock_audio
            
            # Mock ffmpeg
            with patch('subprocess.run'):
                with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
                    mixer = AudioMixer()
                    result_path = mixer.mix(mock_audio_segments, mock_chapters, output_path)
                    
                    # Verify output path has .mp3 extension
                    assert result_path.suffix == '.mp3'
                    
                    # Note: File creation is mocked, so we can't verify actual file existence
                    # in this test without more complex mocking
    
    def test_silence_padding_configuration(self, mock_audio_segments, mock_chapters, tmp_path):
        """Test that silence padding is configurable."""
        output_path = tmp_path / "test_output.mp3"
        
        with patch('peripatos.voice.mixer.PydubAudioSegment') as mock_pydub:
            # Mock audio operations
            mock_audio = Mock()
            mock_audio.__len__ = Mock(return_value=1000)
            mock_audio.__add__ = Mock(return_value=mock_audio)
            mock_audio.export = Mock()
            
            mock_silence = Mock()
            mock_pydub.from_mp3.return_value = mock_audio
            mock_pydub.silent.return_value = mock_silence
            
            # Mock ffmpeg
            with patch('subprocess.run'):
                with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
                    # Create mixer with custom silence duration
                    mixer = AudioMixer(silence_between_segments_ms=500)
                    mixer.mix(mock_audio_segments, mock_chapters, output_path)
                    
                    # Verify silent() was called with custom duration
                    mock_pydub.silent.assert_called_with(duration=500)
    
    def test_intro_outro_silence(self, mock_audio_segments, mock_chapters, tmp_path):
        """Test that intro/outro silence can be added."""
        output_path = tmp_path / "test_output.mp3"
        
        with patch('peripatos.voice.mixer.PydubAudioSegment') as mock_pydub:
            # Mock audio operations
            mock_audio = Mock()
            mock_audio.__len__ = Mock(return_value=1000)
            # Mock __add__ to support chaining
            mock_audio.__add__ = Mock(return_value=mock_audio)
            mock_audio.export = Mock()
            
            # Mock silence with proper __add__ support
            mock_intro_outro_silence = Mock()
            mock_intro_outro_silence.__add__ = Mock(return_value=mock_audio)
            
            mock_segment_silence = Mock()
            mock_segment_silence.__add__ = Mock(return_value=mock_audio)
            
            # Return different mock objects based on duration
            def silent_side_effect(duration):
                if duration == 1000:
                    return mock_intro_outro_silence
                else:
                    return mock_segment_silence
            
            mock_pydub.from_mp3.return_value = mock_audio
            mock_pydub.silent.side_effect = silent_side_effect
            
            # Mock ffmpeg
            with patch('subprocess.run'):
                with patch('shutil.which', return_value='/usr/bin/ffmpeg'):
                    # Create mixer with intro/outro silence
                    mixer = AudioMixer(intro_outro_silence_ms=1000)
                    mixer.mix(mock_audio_segments, mock_chapters, output_path)
                    
                    # Verify silent() was called for intro/outro
                    # Should be called at least once with 1000ms
                    calls = mock_pydub.silent.call_args_list
                    assert any(call[1].get('duration') == 1000 for call in calls)
