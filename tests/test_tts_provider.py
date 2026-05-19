from pathlib import Path
from peripatos_core.providers.tts import TTSProvider
from peripatos_core.providers.tts_stub import StubTTSProvider


def test_stub_returns_path():
    provider = StubTTSProvider()
    path = provider.synthesize("Hello world")
    assert isinstance(path, Path)
    assert path.exists()
    assert path.suffix == ".mp3"


def test_stub_records_calls():
    provider = StubTTSProvider()
    provider.synthesize("Hello", speaker_voice="en-US-AriaNeural")
    assert len(provider.calls) == 1
    assert provider.calls[0] == ("Hello", "en-US-AriaNeural")


def test_stub_is_tts_provider():
    provider = StubTTSProvider()
    assert isinstance(provider, TTSProvider)


def test_stub_file_has_content():
    provider = StubTTSProvider()
    path = provider.synthesize("test")
    assert path.stat().st_size > 0
