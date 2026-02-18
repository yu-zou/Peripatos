"""Tests for peripatos.models - comprehensive TDD test suite."""

import pytest
from pathlib import Path
from peripatos.models import (
    PaperMetadata,
    SectionInfo,
    DialogueTurn,
    DialogueScript,
    AudioSegment,
    ChapterMarker,
    GeneratedPodcast,
    SectionType,
    PersonaType,
    SpeakerRole,
    LanguageMode,
    TTSEngine,
    LLMProvider,
)


class TestEnums:
    """Test all enum definitions."""

    def test_persona_type_has_four_values(self):
        """PersonaType should have exactly 4 values: SKEPTIC, ENTHUSIAST, TUTOR, PEER."""
        personas = list(PersonaType)
        assert len(personas) == 4
        persona_names = {p.name for p in personas}
        assert persona_names == {"SKEPTIC", "ENTHUSIAST", "TUTOR", "PEER"}

    def test_speaker_role_has_two_values(self):
        """SpeakerRole should have exactly 2 values: HOST, EXPERT."""
        roles = list(SpeakerRole)
        assert len(roles) == 2
        role_names = {r.name for r in roles}
        assert role_names == {"HOST", "EXPERT"}

    def test_section_type_has_nine_values(self):
        """SectionType should have all 9 section types."""
        sections = list(SectionType)
        assert len(sections) == 9
        section_names = {s.name for s in sections}
        expected = {
            "ABSTRACT",
            "INTRODUCTION",
            "METHODOLOGY",
            "EXPERIMENTS",
            "RESULTS",
            "DISCUSSION",
            "CONCLUSION",
            "REFERENCES",
            "OTHER",
        }
        assert section_names == expected

    def test_language_mode_has_two_values(self):
        """LanguageMode should have EN and ZH_EN."""
        modes = list(LanguageMode)
        assert len(modes) == 2
        mode_names = {m.name for m in modes}
        assert mode_names == {"EN", "ZH_EN"}

    def test_tts_engine_has_two_values(self):
        """TTSEngine should have OPENAI and EDGE_TTS."""
        engines = list(TTSEngine)
        assert len(engines) == 2
        engine_names = {e.name for e in engines}
        assert engine_names == {"OPENAI", "EDGE_TTS"}

    def test_llm_provider_has_two_values(self):
        """LLMProvider should have OPENAI and ANTHROPIC."""
        providers = list(LLMProvider)
        assert len(providers) == 2
        provider_names = {p.name for p in providers}
        assert provider_names == {"OPENAI", "ANTHROPIC"}


class TestSectionInfo:
    """Test SectionInfo dataclass."""

    def test_section_info_instantiation(self):
        """SectionInfo should be instantiable with title, content, and section_type."""
        section = SectionInfo(
            title="Introduction",
            content="# Introduction\n\nThis is the introduction.",
            section_type=SectionType.INTRODUCTION,
        )
        assert section.title == "Introduction"
        assert section.content == "# Introduction\n\nThis is the introduction."
        assert section.section_type == SectionType.INTRODUCTION

    def test_section_info_repr(self):
        """SectionInfo should have a non-empty __repr__."""
        section = SectionInfo(
            title="Methodology",
            content="Methods used in this study.",
            section_type=SectionType.METHODOLOGY,
        )
        repr_str = repr(section)
        assert len(repr_str) > 0
        assert "SectionInfo" in repr_str or "Methodology" in repr_str


class TestPaperMetadata:
    """Test PaperMetadata dataclass."""

    def test_paper_metadata_with_arxiv_id(self):
        """PaperMetadata should support arxiv_id as optional field."""
        sections = [
            SectionInfo(
                title="Abstract",
                content="Abstract content",
                section_type=SectionType.ABSTRACT,
            )
        ]
        paper = PaperMetadata(
            title="Sample Paper",
            authors=["Alice", "Bob"],
            abstract="This is an abstract",
            arxiv_id="2310.12345",
            source_path=Path("/tmp/paper.pdf"),
            sections=sections,
        )
        assert paper.title == "Sample Paper"
        assert paper.authors == ["Alice", "Bob"]
        assert paper.arxiv_id == "2310.12345"
        assert len(paper.sections) == 1

    def test_paper_metadata_without_arxiv_id(self):
        """PaperMetadata should work without arxiv_id (None by default)."""
        sections = [
            SectionInfo(
                title="Abstract",
                content="Abstract content",
                section_type=SectionType.ABSTRACT,
            )
        ]
        paper = PaperMetadata(
            title="Local Paper",
            authors=["Charlie"],
            abstract="Another abstract",
            source_path=Path("/home/user/papers/local.pdf"),
            sections=sections,
        )
        assert paper.title == "Local Paper"
        assert paper.arxiv_id is None
        assert isinstance(paper.source_path, Path)

    def test_paper_metadata_repr(self):
        """PaperMetadata should have a non-empty __repr__."""
        sections = [
            SectionInfo(
                title="Intro",
                content="Content",
                section_type=SectionType.INTRODUCTION,
            )
        ]
        paper = PaperMetadata(
            title="Test Paper",
            authors=["Author"],
            abstract="Abstract",
            source_path=Path("/tmp/test.pdf"),
            sections=sections,
        )
        repr_str = repr(paper)
        assert len(repr_str) > 0


class TestDialogueTurn:
    """Test DialogueTurn dataclass."""

    def test_dialogue_turn_instantiation(self):
        """DialogueTurn should be instantiable with speaker, text, and section_ref."""
        turn = DialogueTurn(
            speaker=SpeakerRole.HOST,
            text="What is the main contribution?",
            section_ref="introduction",
        )
        assert turn.speaker == SpeakerRole.HOST
        assert turn.text == "What is the main contribution?"
        assert turn.section_ref == "introduction"

    def test_dialogue_turn_repr(self):
        """DialogueTurn should have a non-empty __repr__."""
        turn = DialogueTurn(
            speaker=SpeakerRole.EXPERT,
            text="Our approach uses transformers.",
            section_ref="methodology",
        )
        repr_str = repr(turn)
        assert len(repr_str) > 0
        assert "DialogueTurn" in repr_str or "HOST" in repr_str or "EXPERT" in repr_str


class TestDialogueScript:
    """Test DialogueScript dataclass."""

    def test_dialogue_script_instantiation(self):
        """DialogueScript should contain metadata, turns, persona_type, and language_mode."""
        sections = [
            SectionInfo(
                title="Abstract",
                content="Abstract",
                section_type=SectionType.ABSTRACT,
            )
        ]
        paper = PaperMetadata(
            title="Paper",
            authors=["Author"],
            abstract="Abstract",
            source_path=Path("/tmp/paper.pdf"),
            sections=sections,
        )
        turns = [
            DialogueTurn(
                speaker=SpeakerRole.HOST,
                text="Let's discuss this paper.",
                section_ref="intro",
            ),
            DialogueTurn(
                speaker=SpeakerRole.EXPERT,
                text="Great! Here are the details.",
                section_ref="intro",
            ),
        ]
        script = DialogueScript(
            paper_metadata=paper,
            turns=turns,
            persona_type=PersonaType.SKEPTIC,
            language_mode=LanguageMode.EN,
        )
        assert script.paper_metadata == paper
        assert len(script.turns) == 2
        assert script.persona_type == PersonaType.SKEPTIC
        assert script.language_mode == LanguageMode.EN

    def test_dialogue_script_repr(self):
        """DialogueScript should have a non-empty __repr__."""
        sections = [
            SectionInfo(
                title="Intro",
                content="Intro",
                section_type=SectionType.INTRODUCTION,
            )
        ]
        paper = PaperMetadata(
            title="Paper",
            authors=["Author"],
            abstract="Abstract",
            source_path=Path("/tmp/paper.pdf"),
            sections=sections,
        )
        script = DialogueScript(
            paper_metadata=paper,
            turns=[],
            persona_type=PersonaType.TUTOR,
            language_mode=LanguageMode.ZH_EN,
        )
        repr_str = repr(script)
        assert len(repr_str) > 0


class TestAudioSegment:
    """Test AudioSegment dataclass."""

    def test_audio_segment_instantiation(self):
        """AudioSegment should contain speaker, audio_bytes, duration, and text."""
        audio_bytes = b"\x00\x01\x02\x03"
        segment = AudioSegment(
            speaker=SpeakerRole.HOST,
            audio_bytes=audio_bytes,
            duration_seconds=2.5,
            text="This is the audio segment.",
        )
        assert segment.speaker == SpeakerRole.HOST
        assert segment.audio_bytes == audio_bytes
        assert segment.duration_seconds == 2.5
        assert segment.text == "This is the audio segment."

    def test_audio_segment_repr(self):
        """AudioSegment should have a non-empty __repr__."""
        segment = AudioSegment(
            speaker=SpeakerRole.EXPERT,
            audio_bytes=b"audio",
            duration_seconds=1.0,
            text="Expert speaking",
        )
        repr_str = repr(segment)
        assert len(repr_str) > 0


class TestChapterMarker:
    """Test ChapterMarker dataclass."""

    def test_chapter_marker_instantiation(self):
        """ChapterMarker should contain title, start_time_ms, and end_time_ms."""
        marker = ChapterMarker(
            title="Introduction",
            start_time_ms=0,
            end_time_ms=30000,
        )
        assert marker.title == "Introduction"
        assert marker.start_time_ms == 0
        assert marker.end_time_ms == 30000

    def test_chapter_marker_repr(self):
        """ChapterMarker should have a non-empty __repr__."""
        marker = ChapterMarker(
            title="Methodology",
            start_time_ms=30000,
            end_time_ms=60000,
        )
        repr_str = repr(marker)
        assert len(repr_str) > 0


class TestGeneratedPodcast:
    """Test GeneratedPodcast dataclass."""

    def test_generated_podcast_instantiation(self):
        """GeneratedPodcast should contain paper_metadata, audio_path, chapters, duration, and persona_type."""
        sections = [
            SectionInfo(
                title="Abstract",
                content="Abstract",
                section_type=SectionType.ABSTRACT,
            )
        ]
        paper = PaperMetadata(
            title="Paper",
            authors=["Author"],
            abstract="Abstract",
            source_path=Path("/tmp/paper.pdf"),
            sections=sections,
        )
        chapters = [
            ChapterMarker(title="Intro", start_time_ms=0, end_time_ms=10000),
            ChapterMarker(title="Main", start_time_ms=10000, end_time_ms=20000),
        ]
        podcast = GeneratedPodcast(
            paper_metadata=paper,
            audio_path=Path("/tmp/output.mp3"),
            chapters=chapters,
            duration_seconds=20.0,
            persona_type=PersonaType.ENTHUSIAST,
        )
        assert podcast.paper_metadata == paper
        assert podcast.audio_path == Path("/tmp/output.mp3")
        assert len(podcast.chapters) == 2
        assert podcast.duration_seconds == 20.0
        assert podcast.persona_type == PersonaType.ENTHUSIAST

    def test_generated_podcast_repr(self):
        """GeneratedPodcast should have a non-empty __repr__."""
        sections = [
            SectionInfo(
                title="Abstract",
                content="Abstract",
                section_type=SectionType.ABSTRACT,
            )
        ]
        paper = PaperMetadata(
            title="Paper",
            authors=["Author"],
            abstract="Abstract",
            source_path=Path("/tmp/paper.pdf"),
            sections=sections,
        )
        podcast = GeneratedPodcast(
            paper_metadata=paper,
            audio_path=Path("/tmp/output.mp3"),
            chapters=[],
            duration_seconds=10.0,
            persona_type=PersonaType.PEER,
        )
        repr_str = repr(podcast)
        assert len(repr_str) > 0


class TestModelIntegration:
    """Integration tests combining multiple models."""

    def test_all_models_are_importable(self):
        """All data models should be importable without errors."""
        # This test passes if imports at the top of this file succeed
        assert PaperMetadata is not None
        assert DialogueScript is not None
        assert AudioSegment is not None
        assert GeneratedPodcast is not None

    def test_full_workflow_models(self):
        """Test creating a complete paper-to-podcast workflow with all models."""
        # Create paper with sections
        sections = [
            SectionInfo(
                title="Abstract",
                content="# Abstract\nThis paper presents...",
                section_type=SectionType.ABSTRACT,
            ),
            SectionInfo(
                title="Introduction",
                content="# Introduction\nBackground...",
                section_type=SectionType.INTRODUCTION,
            ),
        ]
        paper = PaperMetadata(
            title="AI Research Paper",
            authors=["Dr. Alice", "Dr. Bob"],
            abstract="A comprehensive study of transformers",
            arxiv_id="2310.00001",
            source_path=Path("/papers/ai_paper.pdf"),
            sections=sections,
        )

        # Create dialogue script
        turns = [
            DialogueTurn(
                speaker=SpeakerRole.HOST,
                text="Welcome to this discussion of AI research.",
                section_ref="intro",
            ),
            DialogueTurn(
                speaker=SpeakerRole.EXPERT,
                text="Thank you for having me. This paper explores...",
                section_ref="intro",
            ),
        ]
        script = DialogueScript(
            paper_metadata=paper,
            turns=turns,
            persona_type=PersonaType.TUTOR,
            language_mode=LanguageMode.EN,
        )

        # Create chapters
        chapters = [
            ChapterMarker(title="Intro", start_time_ms=0, end_time_ms=5000),
            ChapterMarker(title="Main Content", start_time_ms=5000, end_time_ms=15000),
        ]

        # Create podcast
        podcast = GeneratedPodcast(
            paper_metadata=paper,
            audio_path=Path("/output/podcast.mp3"),
            chapters=chapters,
            duration_seconds=15.0,
            persona_type=PersonaType.TUTOR,
        )

        # Verify everything is linked correctly
        assert podcast.paper_metadata.arxiv_id == "2310.00001"
        assert len(podcast.chapters) == 2
        assert podcast.persona_type == PersonaType.TUTOR
