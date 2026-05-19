"""TTS provider abstraction for Peripatos Core."""
from __future__ import annotations
import asyncio
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from peripatos_core.config import TTSConfig


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    @abstractmethod
    def synthesize(self, text: str, speaker_voice: str | None = None) -> Path:
        """Synthesize text to speech and return path to the audio file (mp3/wav)."""


class EdgeTTSProvider(TTSProvider):
    """TTS provider using edge-tts (Microsoft Edge TTS, no API key required)."""

    def __init__(self, config: TTSConfig) -> None:
        self._voice = config.voice

    def synthesize(self, text: str, speaker_voice: str | None = None) -> Path:
        from peripatos_core.exceptions import TTSError
        import edge_tts
        voice = speaker_voice or self._voice
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        output_path = Path(tmp.name)
        try:
            communicate = edge_tts.Communicate(text, voice)
            asyncio.run(communicate.save(str(output_path)))
        except Exception as exc:
            raise TTSError(f"edge-tts synthesis failed: {exc}") from exc
        return output_path


class OpenAICompatibleTTSProvider(TTSProvider):
    """TTS provider using any OpenAI-compatible TTS API."""

    def __init__(self, config: TTSConfig) -> None:
        import openai
        self._client = openai.OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self._model = config.model
        self._voice = config.voice

    def synthesize(self, text: str, speaker_voice: str | None = None) -> Path:
        from peripatos_core.exceptions import TTSError
        voice = speaker_voice or self._voice
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        output_path = Path(tmp.name)
        try:
            response = self._client.audio.speech.create(
                model=self._model,
                voice=voice,
                input=text,
            )
            response.stream_to_file(str(output_path))
        except Exception as exc:
            raise TTSError(f"OpenAI-compatible TTS failed: {exc}") from exc
        return output_path
