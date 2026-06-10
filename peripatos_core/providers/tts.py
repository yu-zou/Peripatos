"""TTS provider abstraction for Peripatos Core."""
from __future__ import annotations

import asyncio
import logging
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path

from peripatos_core.config import TTSConfig

logger = logging.getLogger(__name__)

# edge-tts sometimes returns NoAudioReceived on rapid sequential calls.
# Retry with backoff to handle this transient failure.
_EDGE_TTS_MAX_RETRIES = 5
_EDGE_TTS_RETRY_DELAY = 2.0  # seconds, doubles per attempt
_EDGE_TTS_CIRCUIT_BREAKER_THRESHOLD = 3  # after N consecutive failures, fail fast


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    @abstractmethod
    def synthesize(self, text: str, speaker_voice: str | None = None) -> Path:
        """Synthesize text to speech and return path to the audio file (mp3/wav)."""


class EdgeTTSProvider(TTSProvider):
    """TTS provider using edge-tts (Microsoft Edge TTS, no API key required)."""

    def __init__(self, config: TTSConfig) -> None:
        self._voice = config.voice
        self._consecutive_failures = 0

    def synthesize(self, text: str, speaker_voice: str | None = None) -> Path:
        from peripatos_core.exceptions import TTSError
        import edge_tts

        # Circuit breaker: if we've had N consecutive failures across calls,
        # the TTS service is likely down or rate-limiting — fail fast.
        if self._consecutive_failures >= _EDGE_TTS_CIRCUIT_BREAKER_THRESHOLD:
            raise TTSError(
                f"edge-tts circuit breaker open — {_EDGE_TTS_CIRCUIT_BREAKER_THRESHOLD} "
                f"consecutive synthesis failures. The TTS service is likely unavailable "
                f"or rate-limiting. Wait before retrying."
            )

        voice = speaker_voice or self._voice
        last_exc: Exception | None = None

        for attempt in range(1, _EDGE_TTS_MAX_RETRIES + 1):
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp.close()
            output_path = Path(tmp.name)
            try:
                communicate = edge_tts.Communicate(text, voice)
                # Timeout per-attempt to prevent hangs on stalled websocket connections
                try:
                    asyncio.run(asyncio.wait_for(
                        communicate.save(str(output_path)),
                        timeout=30.0,
                    ))
                except asyncio.TimeoutError:
                    raise TTSError(
                        "edge-tts synthesis timed out after 30s — "
                        "websocket connection may have stalled"
                    )
                # Verify we actually got audio content
                if output_path.stat().st_size == 0:
                    raise TTSError("edge-tts returned empty audio file")
                # Success — reset circuit breaker
                self._consecutive_failures = 0
                return output_path
            except Exception as exc:
                last_exc = exc
                output_path.unlink(missing_ok=True)
                if attempt < _EDGE_TTS_MAX_RETRIES:
                    delay = _EDGE_TTS_RETRY_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "edge-tts synthesis failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt, _EDGE_TTS_MAX_RETRIES, delay, exc,
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "edge-tts synthesis failed after %d attempts: %s",
                        _EDGE_TTS_MAX_RETRIES, exc,
                    )

        # All retries failed — increment circuit breaker
        self._consecutive_failures += 1
        raise TTSError(f"edge-tts synthesis failed after {_EDGE_TTS_MAX_RETRIES} retries: {last_exc}") from last_exc


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
