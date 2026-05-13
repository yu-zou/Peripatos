"""Integration tests for chapter consolidation + signpost insertion in CLI pipeline."""
from __future__ import annotations

from pathlib import Path

from peripatos.brain.chapters import ChapterGroup
from peripatos.cli import (
    _build_chapters,
    _consolidate_and_insert_signposts,
)
from peripatos.models import (
    AudioSegment,
    DialogueScript,
    DialogueTurn,
    LanguageMode,
    PaperMetadata,
    PersonaType,
    SectionInfo,
    SectionType,
    SpeakerRole,
)


def _make_turn(section_ref: str, text: str = "t", speaker: SpeakerRole = SpeakerRole.HOST) -> DialogueTurn:
    return DialogueTurn(speaker=speaker, text=text, section_ref=section_ref)


def _make_paper(section_titles: list[str]) -> PaperMetadata:
    return PaperMetadata(
        title="Test Paper",
        authors=["A"],
        abstract="abs",
        source_path=Path("/tmp/test.pdf"),
        sections=[
            SectionInfo(title=t, content="c", section_type=SectionType.OTHER)
            for t in section_titles
        ],
    )


def _make_script(turns: list[DialogueTurn], section_titles: list[str]) -> DialogueScript:
    return DialogueScript(
        paper_metadata=_make_paper(section_titles),
        turns=turns,
        persona_type=PersonaType.TUTOR,
        language_mode=LanguageMode.EN,
    )


class TestConsolidateAndInsertSignposts:
    def test_single_section_no_signposts(self):
        """A 1-section paper produces 1 chapter group and 0 signposts."""
        turns = [_make_turn("intro"), _make_turn("intro"), _make_turn("intro")]
        script = _make_script(turns, ["intro"])
        new_script, groups = _consolidate_and_insert_signposts(script)
        assert len(groups) == 1
        assert len(new_script.turns) == 3
        assert all(not t.is_signpost for t in new_script.turns)

    def test_multi_section_inserts_signposts(self):
        """Multi-section dialogue gets signpost turns before each non-first chapter."""
        turns = []
        for sec in ["s1", "s2", "s3", "s4", "s5", "s6", "s7"]:
            turns.append(_make_turn(sec, text=f"Talking about {sec}"))
            turns.append(_make_turn(sec, text=f"More about {sec}", speaker=SpeakerRole.EXPERT))
        script = _make_script(turns, ["s1", "s2", "s3", "s4", "s5", "s6", "s7"])

        new_script, groups = _consolidate_and_insert_signposts(script)

        assert 2 <= len(groups) <= 5
        signpost_turns = [t for t in new_script.turns if t.is_signpost]
        assert len(signpost_turns) == len(groups) - 1
        assert all(t.speaker == SpeakerRole.HOST for t in signpost_turns)
        for sp in signpost_turns:
            assert sp.is_signpost is True
            assert sp.chapter_title is not None

    def test_signpost_position_before_chapter_start(self):
        """Signposts are inserted immediately before the first turn of their chapter."""
        turns = [
            _make_turn("a"), _make_turn("a"),
            _make_turn("b"), _make_turn("b"),
            _make_turn("c"), _make_turn("c"),
        ]
        script = _make_script(turns, ["a", "b", "c"])
        new_script, groups = _consolidate_and_insert_signposts(script)
        assert len(groups) == 3
        signposts = [(i, t) for i, t in enumerate(new_script.turns) if t.is_signpost]
        assert len(signposts) == 2
        i1, _ = signposts[0]
        assert new_script.turns[i1 + 1].section_ref == "b"
        i2, _ = signposts[1]
        assert new_script.turns[i2 + 1].section_ref == "c"

    def test_returns_groups_with_correct_indices_after_insertion(self):
        """Returned chapter groups reflect updated turn indices (after signpost insertion)."""
        turns = [
            _make_turn("a"), _make_turn("a"),
            _make_turn("b"), _make_turn("b"),
        ]
        script = _make_script(turns, ["a", "b"])
        new_script, groups = _consolidate_and_insert_signposts(script)
        for group in groups:
            for idx in group.turn_indices:
                assert 0 <= idx < len(new_script.turns)
        total_indices = sum(len(g.turn_indices) for g in groups)
        assert total_indices == len(new_script.turns)

    def test_empty_script_handled(self):
        """Empty turns produces empty groups and unchanged script."""
        script = _make_script([], [])
        new_script, groups = _consolidate_and_insert_signposts(script)
        assert groups == []
        assert new_script.turns == []


class TestBuildChaptersWithGroups:
    def test_build_chapters_uses_group_titles(self):
        """_build_chapters uses ChapterGroup titles when groups are provided."""
        turns = [
            _make_turn("a"), _make_turn("a"),
            _make_turn("b"),
        ]
        script = _make_script(turns, ["a", "b"])
        segments = [
            AudioSegment(speaker=SpeakerRole.HOST, audio_bytes=b"x", duration_seconds=1.0, text="t"),
            AudioSegment(speaker=SpeakerRole.HOST, audio_bytes=b"x", duration_seconds=1.0, text="t"),
            AudioSegment(speaker=SpeakerRole.HOST, audio_bytes=b"x", duration_seconds=1.0, text="t"),
        ]
        groups = [
            ChapterGroup(title="Custom Title", turn_indices=[0, 1], section_refs=["a"]),
            ChapterGroup(title="Other Title", turn_indices=[2], section_refs=["b"]),
        ]
        chapters, _total_ms = _build_chapters(
            script, segments, silence_between_ms=100, chapter_groups=groups,
        )
        assert len(chapters) == 2
        assert chapters[0].title == "Custom Title"
        assert chapters[1].title == "Other Title"
        assert chapters[0].start_time_ms == 0
        assert chapters[0].end_time_ms == 2200
        assert chapters[1].start_time_ms == 2200

    def test_build_chapters_backward_compat_without_groups(self):
        """When chapter_groups is None, _build_chapters uses paper sections (legacy behavior preserved)."""
        turns = [_make_turn("Intro"), _make_turn("Methods")]
        script = _make_script(turns, ["Intro", "Methods"])
        segments = [
            AudioSegment(speaker=SpeakerRole.HOST, audio_bytes=b"x", duration_seconds=1.0, text="t"),
            AudioSegment(speaker=SpeakerRole.HOST, audio_bytes=b"x", duration_seconds=1.0, text="t"),
        ]
        chapters, _ = _build_chapters(script, segments, silence_between_ms=100)
        titles = [c.title for c in chapters]
        assert "Intro" in titles
        assert "Methods" in titles


class TestSinglePassPipelineIntegration:
    def test_signpost_count_matches_chapter_count_minus_one(self):
        """For any n-section input, signpost count == final chapter count - 1."""
        turns = []
        for sec in ["s1", "s2", "s3", "s4"]:
            turns.append(_make_turn(sec))
            turns.append(_make_turn(sec, speaker=SpeakerRole.EXPERT))
        script = _make_script(turns, ["s1", "s2", "s3", "s4"])
        new_script, groups = _consolidate_and_insert_signposts(script)
        signposts = [t for t in new_script.turns if t.is_signpost]
        assert len(signposts) == max(0, len(groups) - 1)
