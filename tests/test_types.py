"""Tests for core type definitions."""
# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false
import warnings
from pathlib import Path

from peripatos_core.types import (
    ArchetypeId,
    AudioSegment,
    ChapterMark,
    DialogueScript,
    DialogueTurn,
    PaperMetadata,
    _calculate_target_turns,
)


def test_archetype_id_values():
    assert ArchetypeId.PEER == "peer"
    assert ArchetypeId.SKEPTIC == "skeptic"
    assert ArchetypeId.TUTOR == "tutor"
    assert ArchetypeId.ENTHUSIAST == "enthusiast"


def test_dialogue_turn():
    turn = DialogueTurn(speaker="Host", text="Hello", archetype=ArchetypeId.PEER)
    assert turn.speaker == "Host"
    assert turn.archetype == ArchetypeId.PEER


def test_dialogue_script_default_empty():
    script = DialogueScript(title="Test Paper")
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        assert script.turns == []


def test_audio_segment():
    seg = AudioSegment(speaker="Host", text="Hi", audio_path=Path("/tmp/a.mp3"), duration_s=1.5)
    assert seg.duration_s == 1.5


def test_chapter_mark():
    ch = ChapterMark(title="Intro", start_ms=0, end_ms=5000)
    assert ch.end_ms == 5000


def test_paper_metadata_defaults():
    meta = PaperMetadata(title="My Paper")
    assert meta.authors == []
    assert meta.abstract == ""
    assert meta.arxiv_id is None


def test_dialogue_script_has_intro_outro_fields():
    s = DialogueScript(title="Test")
    assert hasattr(s, "intro_turns")
    assert hasattr(s, "outro_turns")
    assert s.intro_turns == []
    assert s.outro_turns == []


def test_calculate_target_turns_12_page_paper():
    # 12 pages * 300 words = 3600 words, * 2 = 24 turns
    paper = "word " * 3600
    assert _calculate_target_turns(paper) == 24


def test_calculate_target_turns_short_paper_min():
    paper = "word " * 100  # <5 pages → would be <10, clamped to 10
    assert _calculate_target_turns(paper) == 10


def test_calculate_target_turns_long_paper_max():
    paper = "word " * 100000  # >>20 pages → clamped to 40
    assert _calculate_target_turns(paper) == 40
