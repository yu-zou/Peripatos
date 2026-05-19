"""Tests for core type definitions."""
# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownMemberType=false
from pathlib import Path

from peripatos_core.types import (
    ArchetypeId,
    AudioSegment,
    ChapterMark,
    DialogueScript,
    DialogueTurn,
    PaperMetadata,
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
