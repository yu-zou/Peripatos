"""Stub TTS provider for unit tests - generates valid silent MP3 via pydub."""
from __future__ import annotations
import tempfile
from pathlib import Path
from pydub import AudioSegment as PydubAudioSegment  # type: ignore[reportMissingImports]
from peripatos_core.providers.tts import TTSProvider


class StubTTSProvider(TTSProvider):
    """Returns a valid silent MP3 file for testing."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def synthesize(self, text: str, speaker_voice: str | None = None) -> Path:
        self.calls.append((text, speaker_voice))
        silence = PydubAudioSegment.silent(duration=100, frame_rate=44100)
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        silence.export(tmp.name, format="mp3")
        return Path(tmp.name)
