"""Stub TTS provider for unit tests - writes silent MP3 bytes, no network calls."""
from __future__ import annotations
import tempfile
from pathlib import Path
from peripatos_core.providers.tts import TTSProvider

_SILENT_MP3 = bytes([
    0xFF, 0xFB, 0x90, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
])


class StubTTSProvider(TTSProvider):
    """Returns a tiny silent MP3 file for testing."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def synthesize(self, text: str, speaker_voice: str | None = None) -> Path:
        self.calls.append((text, speaker_voice))
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.write(_SILENT_MP3)
        tmp.close()
        return Path(tmp.name)
