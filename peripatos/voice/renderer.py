"""Audio renderer orchestrator with TTS engine selection and smart chunking."""

import logging
from io import BytesIO
from typing import Optional, Callable
from pydub import AudioSegment as PydubAudioSegment

from peripatos.config import PeripatosConfig
from peripatos.models import DialogueScript, AudioSegment, SpeakerRole
from peripatos.voice.openai_tts import OpenAITTSEngine
from peripatos.voice.edge_tts_engine import EdgeTTSEngine


logger = logging.getLogger(__name__)


class AudioRenderer:
    """Audio renderer that orchestrates TTS engine selection and audio generation.
    
    This class handles:
    - Automatic engine selection (OpenAI with fallback to edge-tts)
    - Voice routing based on speaker roles (HOST/EXPERT)
    - Silence padding between dialogue turns (300ms)
    - Progress callbacks for CLI integration
    
    Attributes:
        config: Peripatos configuration
        active_engine: The selected TTS engine (OpenAI or edge-tts)
        active_engine_name: Name of the active engine ("openai" or "edge-tts")
    """
    
    SILENCE_DURATION_MS = 300  # 300ms silence between turns
    
    def __init__(self, config: PeripatosConfig):
        """Initialize the audio renderer.
        
        Args:
            config: Peripatos configuration with TTS settings.
        """
        self.config = config
        self.active_engine = None
        self.active_engine_name = None
        
        # Select TTS engine based on configuration and availability
        self._select_engine()
    
    def _select_engine(self):
        """Select the appropriate TTS engine based on config and availability.
        
        Priority:
        1. If config.tts_engine == "openai" and OpenAI is available → use OpenAI
        2. Otherwise → fall back to edge-tts with a warning
        """
        # Try OpenAI first if configured
        if self.config.tts_engine == "openai":
            openai_engine = OpenAITTSEngine(api_key=self.config.openai_api_key)
            
            if openai_engine.is_available():
                self.active_engine = openai_engine
                self.active_engine_name = "openai"
                logger.info("Using OpenAI TTS engine")
                return
            else:
                logger.warning(
                    "OpenAI TTS engine configured but API key not available. "
                    "Falling back to edge-tts."
                )
        
        # Fall back to edge-tts
        edge_engine = EdgeTTSEngine()
        self.active_engine = edge_engine
        self.active_engine_name = "edge-tts"
        logger.info("Using edge-tts engine")
    
    def render(
        self,
        script: DialogueScript,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> list[AudioSegment]:
        """Render a dialogue script to audio segments.
        
        Args:
            script: DialogueScript containing turns to render
            progress_callback: Optional callback function(current, total) for progress
            
        Returns:
            List of AudioSegment objects, one per dialogue turn
        """
        segments = []
        total_turns = len(script.turns)
        
        logger.info(f"Rendering {total_turns} dialogue turns with {self.active_engine_name}")
        
        for idx, turn in enumerate(script.turns):
            # Select voice based on speaker role
            voice = self._get_voice_for_speaker(turn.speaker)
            
            # Synthesize audio using the active engine
            audio_bytes = self._synthesize_with_engine(turn.text, voice)
            
            # Calculate duration
            duration = self._get_audio_duration(audio_bytes)
            
            # Create AudioSegment
            segment = AudioSegment(
                speaker=turn.speaker,
                audio_bytes=audio_bytes,
                duration_seconds=duration,
                text=turn.text
            )
            
            segments.append(segment)
            
            # Call progress callback if provided
            if progress_callback:
                progress_callback(idx + 1, total_turns)
        
        logger.info(f"Successfully rendered {len(segments)} audio segments")
        return segments
    
    def _get_voice_for_speaker(self, speaker: SpeakerRole) -> str:
        """Get the appropriate voice for a speaker role.
        
        Args:
            speaker: Speaker role (HOST or EXPERT)
            
        Returns:
            Voice name/identifier for the TTS engine
        """
        if speaker == SpeakerRole.HOST:
            return self.config.tts_voice_host
        else:  # SpeakerRole.EXPERT
            return self.config.tts_voice_expert
    
    def _synthesize_with_engine(self, text: str, voice: str) -> bytes:
        """Synthesize text using the active TTS engine.
        
        Args:
            text: Text to synthesize
            voice: Voice identifier
            
        Returns:
            Audio bytes (MP3 format)
        """
        if self.active_engine_name == "openai":
            return self.active_engine.synthesize(text, voice)
        else:  # edge-tts
            return self.active_engine.synthesize_sync(text, voice)
    
    def _get_audio_duration(self, audio_bytes: bytes) -> float:
        """Calculate duration of audio in seconds.
        
        Args:
            audio_bytes: Audio data in MP3 format
            
        Returns:
            Duration in seconds
        """
        try:
            audio_segment = PydubAudioSegment.from_mp3(BytesIO(audio_bytes))
            return len(audio_segment) / 1000.0  # Convert ms to seconds
        except Exception as e:
            logger.warning(f"Could not determine audio duration: {e}")
            # Rough estimate: ~150 words per minute, ~5 chars per word
            # Assume 10 chars per second of speech
            return len(audio_bytes) / 10.0
    
    def add_silence_padding(self, segments: list[AudioSegment]) -> bytes:
        """Add silence padding between audio segments and merge to single file.
        
        This method is separate from render() to allow testing of padding logic.
        
        Args:
            segments: List of AudioSegment objects
            
        Returns:
            Single merged audio file with 300ms silence between turns
        """
        if not segments:
            return b""
        
        # Create silence segment
        silence = PydubAudioSegment.silent(duration=self.SILENCE_DURATION_MS)
        
        # Build combined audio
        combined = None
        
        for idx, segment in enumerate(segments):
            audio_seg = PydubAudioSegment.from_mp3(BytesIO(segment.audio_bytes))
            
            if combined is None:
                combined = audio_seg
            else:
                # Add silence, then the next segment
                combined = combined + silence + audio_seg
        
        # Export to bytes
        output = BytesIO()
        combined.export(output, format="mp3")
        return output.getvalue()