"""Tests for AudioRenderer."""
import pytest
import importlib
from peripatos_core.audio import AudioRenderer
from peripatos_core.providers.tts_stub import StubTTSProvider
from peripatos_core.types import ArchetypeId, Chapter, ChapterMark, DialogueScript, DialogueTurn
from peripatos_core.exceptions import AudioError


def _make_script(n_turns: int = 3) -> DialogueScript:
    turns = []
    for i in range(n_turns):
        speaker = "Host" if i % 2 == 0 else "Guest"
        turns.append(DialogueTurn(
            speaker=speaker,
            text=f"This is turn {i}.",
        archetype=ArchetypeId.PEER,
        ))
    return DialogueScript(title="Test Episode", chapters=[Chapter(title="", turns=turns)])


def test_render_creates_output_file(tmp_path):
    renderer = AudioRenderer(tts=StubTTSProvider())
    script = _make_script(3)
    output = tmp_path / "output.mp3"
    renderer.render(script, output)
    assert output.exists()
    assert output.stat().st_size > 0


def test_render_returns_chapter_marks(tmp_path):
    renderer = AudioRenderer(tts=StubTTSProvider())
    script = _make_script(3)
    output = tmp_path / "output.mp3"
    chapters = renderer.render(script, output)
    assert isinstance(chapters, list)
    assert len(chapters) == 3
    for ch in chapters:
        assert isinstance(ch, ChapterMark)


def test_render_chapter_titles_match_speakers(tmp_path):
    renderer = AudioRenderer(tts=StubTTSProvider())
    script = _make_script(4)
    output = tmp_path / "output.mp3"
    chapters = renderer.render(script, output)
    speakers = [t.speaker for t in script.turns]
    chapter_titles = [ch.title for ch in chapters]
    assert chapter_titles == speakers


def test_render_empty_script_raises(tmp_path):
    renderer = AudioRenderer(tts=StubTTSProvider())
    script = DialogueScript(title="Empty", chapters=[Chapter(title="", turns=[])])
    with pytest.raises(AudioError, match="empty"):
        renderer.render(script, tmp_path / "output.mp3")


def test_render_output_has_id3_tags(tmp_path):
    renderer = AudioRenderer(tts=StubTTSProvider())
    script = _make_script(2)
    output = tmp_path / "output.mp3"
    renderer.render(script, output)
    ID3 = importlib.import_module("mutagen.id3").ID3
    tags = ID3(str(output))
    assert "TIT2" in tags
    assert tags["TIT2"].text[0] == "Test Episode"


def test_render_voice_map_passed_to_tts(tmp_path):
    stub = StubTTSProvider()
    voice_map = {"Host": "en-US-AriaNeural", "Guest": "en-US-GuyNeural"}
    renderer = AudioRenderer(tts=stub, voice_map=voice_map)
    script = _make_script(2)
    output = tmp_path / "output.mp3"
    renderer.render(script, output)
    voices_used = [call[1] for call in stub.calls]
    assert "en-US-AriaNeural" in voices_used
    assert "en-US-GuyNeural" in voices_used
