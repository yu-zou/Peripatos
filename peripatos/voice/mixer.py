"""Audio mixer with chapter markers using ffmpeg."""

import logging
import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from pydub import AudioSegment as PydubAudioSegment

from peripatos.models import AudioSegment, ChapterMarker


logger = logging.getLogger(__name__)


class MixerError(Exception):
    """Exception raised for audio mixing errors."""
    pass


class AudioMixer:
    """Audio mixer that concatenates segments and injects chapter markers.
    
    This class handles:
    - Concatenation of audio segments with configurable silence padding
    - Generation of ffmpeg chapter metadata in FFMETADATA1 format
    - Injection of chapter markers using ffmpeg subprocess
    - Validation of ffmpeg availability
    
    Attributes:
        silence_between_segments_ms: Silence duration between segments (default 300ms)
        intro_outro_silence_ms: Silence duration at intro/outro (default 0ms)
    """
    
    def __init__(
        self,
        silence_between_segments_ms: int = 300,
        intro_outro_silence_ms: int = 0
    ):
        """Initialize the audio mixer.
        
        Args:
            silence_between_segments_ms: Silence duration between segments in milliseconds
            intro_outro_silence_ms: Silence duration at intro/outro in milliseconds
        """
        self.silence_between_segments_ms = silence_between_segments_ms
        self.intro_outro_silence_ms = intro_outro_silence_ms
    
    def mix(
        self,
        segments: list[AudioSegment],
        chapters: list[ChapterMarker],
        output_path: Path
    ) -> Path:
        """Mix audio segments with chapter markers into final MP3.
        
        Args:
            segments: List of AudioSegment objects to concatenate
            chapters: List of ChapterMarker objects for navigation
            output_path: Path where the final MP3 will be saved
            
        Returns:
            Path to the output MP3 file
            
        Raises:
            MixerError: If segments is empty, ffmpeg is missing, or mixing fails
        """
        # Validate inputs
        if not segments:
            raise MixerError("Cannot mix audio: no segments provided")
        
        # Check ffmpeg availability
        if not self._check_ffmpeg_available():
            raise MixerError(
                "ffmpeg is not installed or not found in PATH. "
                "Please install ffmpeg to use audio mixing functionality. "
                "Visit https://ffmpeg.org/download.html for installation instructions."
            )
        
        logger.info(f"Mixing {len(segments)} audio segments with {len(chapters)} chapters")
        
        try:
            # Step 1: Concatenate audio segments with silence padding
            combined_audio = self._concatenate_segments(segments)
            
            # Step 2: Export combined audio to temporary file
            temp_audio_path = self._export_combined_audio(combined_audio, output_path)
            
            # Step 3: Generate chapter metadata file
            if chapters:
                metadata_file = self._generate_chapter_metadata(chapters)
                
                # Step 4: Inject chapters using ffmpeg
                self._inject_chapters(temp_audio_path, metadata_file, output_path)
                
                # Clean up temporary files
                temp_audio_path.unlink()
                Path(metadata_file).unlink()
            else:
                # No chapters - just move the temp file to output
                temp_audio_path.rename(output_path)
            
            logger.info(f"Successfully mixed audio to {output_path}")
            return output_path
            
        except Exception as e:
            if isinstance(e, MixerError):
                raise
            raise MixerError(f"Failed to mix audio: {e}") from e
    
    def _check_ffmpeg_available(self) -> bool:
        """Check if ffmpeg is available in PATH.
        
        Returns:
            True if ffmpeg is available, False otherwise
        """
        return shutil.which('ffmpeg') is not None
    
    def _concatenate_segments(self, segments: list[AudioSegment]) -> PydubAudioSegment:
        """Concatenate audio segments with silence padding.
        
        Args:
            segments: List of AudioSegment objects
            
        Returns:
            Combined PydubAudioSegment
        """
        combined = None
        
        # Create silence segments
        silence = PydubAudioSegment.silent(duration=self.silence_between_segments_ms)
        intro_outro_silence = None
        if self.intro_outro_silence_ms > 0:
            intro_outro_silence = PydubAudioSegment.silent(duration=self.intro_outro_silence_ms)
        
        # Add intro silence if configured
        if intro_outro_silence is not None:
            combined = intro_outro_silence
        
        # Concatenate all segments with silence between them
        for idx, segment in enumerate(segments):
            # Load audio from bytes
            audio = PydubAudioSegment.from_mp3(BytesIO(segment.audio_bytes))
            
            if combined is None:
                combined = audio
            else:
                # Add silence before this segment (except for first segment)
                combined = combined + silence + audio
        
        # Add outro silence if configured
        if intro_outro_silence is not None and combined is not None:
            combined = combined + intro_outro_silence
        
        return combined
    
    def _export_combined_audio(
        self,
        audio: PydubAudioSegment,
        output_path: Path
    ) -> Path:
        """Export combined audio to temporary file.
        
        Args:
            audio: Combined PydubAudioSegment
            output_path: Desired output path (used to determine temp location)
            
        Returns:
            Path to temporary audio file
        """
        # Create temporary file in same directory as output
        temp_fd, temp_path_str = tempfile.mkstemp(
            suffix='.mp3',
            dir=output_path.parent
        )
        temp_path = Path(temp_path_str)
        
        # Export audio
        audio.export(temp_path, format='mp3')
        
        # Close the file descriptor
        import os
        os.close(temp_fd)
        
        return temp_path
    
    def _generate_chapter_metadata(self, chapters: list[ChapterMarker]) -> str:
        """Generate ffmpeg chapter metadata file in FFMETADATA1 format.
        
        Args:
            chapters: List of ChapterMarker objects
            
        Returns:
            Path to temporary metadata file
        """
        # Create temporary metadata file
        temp_fd, metadata_path = tempfile.mkstemp(suffix='.txt')
        
        with open(metadata_path, 'w') as f:
            # Write FFMETADATA1 header
            f.write(';FFMETADATA1\n')
            
            # Write each chapter
            for chapter in chapters:
                f.write('[CHAPTER]\n')
                f.write('TIMEBASE=1/1000\n')
                f.write(f'START={chapter.start_time_ms}\n')
                f.write(f'END={chapter.end_time_ms}\n')
                f.write(f'title={chapter.title}\n')
        
        # Close the file descriptor
        import os
        os.close(temp_fd)
        
        logger.debug(f"Generated chapter metadata file: {metadata_path}")
        return metadata_path
    
    def _inject_chapters(
        self,
        input_path: Path,
        metadata_path: str,
        output_path: Path
    ):
        """Inject chapter markers into audio using ffmpeg.
        
        Args:
            input_path: Path to input audio file
            metadata_path: Path to metadata file
            output_path: Path to output audio file
            
        Raises:
            MixerError: If ffmpeg command fails
        """
        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-i', metadata_path,
            '-map_metadata', '1',
            '-codec', 'copy',
            '-y',  # Overwrite output file if exists
            str(output_path)
        ]
        
        logger.debug(f"Running ffmpeg command: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )
            logger.debug(f"ffmpeg output: {result.stdout}")
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg failed: {e.stderr}")
            raise MixerError(f"ffmpeg failed to inject chapters: {e.stderr}") from e