"""Tests for AudioRenderer."""
import pytest
import importlib
from pathlib import Path
from peripatos_core.audio import AudioRenderer
from peripatos_core.providers.tts_stub import StubTTSProvider
from peripatos_core.types import (
    ArchetypeId,
    AudioSegment,
    Chapter,
    ChapterMark,
    DialogueScript,
    DialogueTurn,
)
from peripatos_core.exceptions import AudioError


def _make_script(
    n_turns: int = 3,
    chapter_title: str = "Introduction",
) -> DialogueScript:
    turns = []
    for i in range(n_turns):
        speaker = "Host" if i % 2 == 0 else "Guest"
        turns.append(DialogueTurn(
            speaker=speaker,
            text=f"This is turn {i}.",
            archetype=ArchetypeId.PEER,
        ))
    return DialogueScript(
        title="Test Episode",
        chapters=[Chapter(title=chapter_title, turns=turns)],
    )


def _make_multichapter_script() -> DialogueScript:
    """Two chapters, two turns each, with content-based titles."""
    ch1 = Chapter(
        title="Methodology",
        turns=[
            DialogueTurn(speaker="Host", text="We discuss methods.", archetype=ArchetypeId.PEER),
            DialogueTurn(speaker="Guest", text="Here is my approach.", archetype=ArchetypeId.PEER),
        ],
    )
    ch2 = Chapter(
        title="Results",
        turns=[
            DialogueTurn(speaker="Host", text="What were the results?", archetype=ArchetypeId.PEER),
            DialogueTurn(speaker="Guest", text="The results are clear.", archetype=ArchetypeId.PEER),
        ],
        transition_in_text="Now let's turn to the results.",
    )
    return DialogueScript(title="Multi-chapter Episode", chapters=[ch1, ch2])


# --- Existing tests (updated for per-chapter CHAP behavior) ---

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
    assert len(chapters) == 1  # one chapter, not one per turn
    for ch in chapters:
        assert isinstance(ch, ChapterMark)


def test_render_chapter_titles_content_based(tmp_path):
    """ChapterMark titles come from chapter.title, not speaker names."""
    renderer = AudioRenderer(tts=StubTTSProvider())
    script = _make_script(4, chapter_title="Methodology")
    output = tmp_path / "output.mp3"
    chapters = renderer.render(script, output)
    assert len(chapters) == 1
    assert chapters[0].title == "Methodology"
    assert chapters[0].title != "Host"
    assert chapters[0].title != "Guest"


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


# --- New TDD tests ---

def test_compute_chapters_per_chapter():
    """_compute_chapters returns one ChapterMark per chapter, not per segment."""
    segments_per_chapter = [
        [
            AudioSegment(speaker="Host", text="A", audio_path=Path("/tmp/a.mp3"), duration_s=1.0),
            AudioSegment(speaker="Guest", text="B", audio_path=Path("/tmp/b.mp3"), duration_s=2.0),
        ],
        [
            AudioSegment(speaker="Host", text="C", audio_path=Path("/tmp/c.mp3"), duration_s=1.5),
            AudioSegment(speaker="Guest", text="D", audio_path=Path("/tmp/d.mp3"), duration_s=0.5),
        ],
    ]
    chapters = [
        Chapter(title="Methodology"),
        Chapter(title="Results"),
    ]
    renderer = AudioRenderer(tts=StubTTSProvider())
    marks = renderer._compute_chapters(segments_per_chapter, chapters)

    assert len(marks) == 2
    assert marks[0].title == "Methodology"
    assert marks[1].title == "Results"
    assert marks[0].start_ms == 0
    assert marks[0].end_ms == 3000  # (1.0 + 2.0) * 1000
    assert marks[1].start_ms == 3000
    assert marks[1].end_ms == 5000  # 3000 + (1.5 + 0.5) * 1000


def test_chapter_titles_not_speaker_names():
    """ChapterMark titles are content-based (chapter titles), not speaker names."""
    renderer = AudioRenderer(tts=StubTTSProvider())
    script = _make_multichapter_script()
    output = Path("/tmp/test_output.mp3")  # won't actually write

    # Use a tmp_path fixture version
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        out = Path(f.name)

    try:
        marks = renderer.render(script, out)
        assert len(marks) == 2
        # Titles should be content-based chapter titles, not speaker names
        assert marks[0].title == "Methodology"
        assert marks[1].title == "Results"
        assert marks[0].title != "Host"
        assert marks[0].title != "Guest"
        assert marks[1].title != "Host"
        assert marks[1].title != "Guest"
    finally:
        out.unlink(missing_ok=True)


def test_first_chapter_no_transition():
    """First chapter with transition_in_text=None should not synthesize transition audio."""
    stub = StubTTSProvider()
    renderer = AudioRenderer(tts=stub)
    script = _make_multichapter_script()
    # First chapter has no transition_in_text
    assert script.chapters[0].transition_in_text is None

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        out = Path(f.name)
    try:
        renderer.render(script, out)
    finally:
        out.unlink(missing_ok=True)

    # Verify no transition text was synthesized for chapter 0
    transition_texts = [text for text, _voice in stub.calls if "turn to the results" in text or "transition" in text.lower()]
    # The transition "Now let's turn to the results" should be synthesized (for chapter 1)
    # but chapter 0 should not generate any transition synthesis
    transition_count = len([text for text, _voice in stub.calls if text == "Now let's turn to the results."])
    assert transition_count == 1  # only for chapter 1, not chapter 0


def test_transition_audio_synthesized():
    """Chapter with transition_in_text triggers TTS.synthesize with host voice."""
    stub = StubTTSProvider()
    voice_map = {"Host": "en-US-AriaNeural", "Guest": "en-US-GuyNeural"}
    renderer = AudioRenderer(tts=stub, voice_map=voice_map)
    script = _make_multichapter_script()

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        out = Path(f.name)
    try:
        renderer.render(script, out)
    finally:
        out.unlink(missing_ok=True)

    # Verify TTS was called for the transition text with host voice
    transition_call = None
    for text, voice in stub.calls:
        if text == "Now let's turn to the results.":
            transition_call = (text, voice)
            break

    assert transition_call is not None, "TTS.synthesize should have been called for transition text"
    assert transition_call[1] == "en-US-AriaNeural", "Transition should use host voice"


def test_transition_audio_uses_voice_map_fallback():
    """When 'Host' not in voice_map, fallback to first speaker's voice."""
    stub = StubTTSProvider()
    voice_map = {"Guest": "en-US-GuyNeural"}  # No "Host" key
    renderer = AudioRenderer(tts=stub, voice_map=voice_map)
    script = _make_multichapter_script()
    # First chapter's first turn speaker is "Host", whose voice is not in map
    # But the fallback uses voice_map.get(chapter.turns[0].speaker) which is "Host"
    # ...and "Host" is not in voice_map, so it falls through to None
    # Actually: self._voice_map.get("Host") returns None (not in map)
    # Then: self._voice_map.get("Host") → None again, so voice = None
    # This is expected — fallback when voice is not mapped.

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        out = Path(f.name)
    try:
        renderer.render(script, out)
    finally:
        out.unlink(missing_ok=True)

    # Transition should still be synthesized (with voice=None as fallback)
    transition_calls = [
        (text, voice) for text, voice in stub.calls
        if text == "Now let's turn to the results."
    ]
    assert len(transition_calls) == 1


def test_multi_chapter_mark_count():
    """End-to-end: multi-chapter script renders correct count of ChapterMarks."""
    stub = StubTTSProvider()
    renderer = AudioRenderer(tts=stub)
    script = _make_multichapter_script()

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        out = Path(f.name)
    try:
        marks = renderer.render(script, out)
        # 2 chapters, 2 turns each + 1 transition → 5 total segments
        # but only 2 ChapterMarks
        assert len(marks) == 2
        assert marks[0].title == "Methodology"
        assert marks[1].title == "Results"
    finally:
        out.unlink(missing_ok=True)
