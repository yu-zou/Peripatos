"""Core data models and type definitions for Peripatos."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


# Enums
class PersonaType(Enum):
    """Persona archetypes for dialogue speakers."""

    SKEPTIC = "skeptic"
    ENTHUSIAST = "enthusiast"
    TUTOR = "tutor"
    PEER = "peer"


class SpeakerRole(Enum):
    """Speaker roles in dialogue."""

    HOST = "host"
    EXPERT = "expert"


class SectionType(Enum):
    """Types of paper sections."""

    ABSTRACT = "abstract"
    INTRODUCTION = "introduction"
    METHODOLOGY = "methodology"
    EXPERIMENTS = "experiments"
    RESULTS = "results"
    DISCUSSION = "discussion"
    CONCLUSION = "conclusion"
    REFERENCES = "references"
    OTHER = "other"


class LanguageMode(Enum):
    """Language modes for audio generation."""

    EN = "en"
    ZH_EN = "zh_en"


class TTSEngine(Enum):
    """Text-to-speech engine providers."""

    OPENAI = "openai"
    EDGE_TTS = "edge_tts"


class LLMProvider(Enum):
    """Large language model providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    GEMINI = "gemini"


# Data Classes
@dataclass
class SectionInfo:
    """Information about a paper section."""

    title: str
    content: str
    section_type: SectionType


@dataclass
class PaperMetadata:
    """Metadata about an academic paper."""

    title: str
    authors: list[str]
    abstract: str
    source_path: Path
    sections: list[SectionInfo]
    arxiv_id: Optional[str] = None


@dataclass
class DialogueTurn:
    """A single turn in a dialogue between host and expert."""

    speaker: SpeakerRole
    text: str
    section_ref: str


@dataclass
class DialogueScript:
    """A complete dialogue script for a paper."""

    paper_metadata: PaperMetadata
    turns: list[DialogueTurn]
    persona_type: PersonaType
    language_mode: LanguageMode


@dataclass
class AudioSegment:
    """A segment of generated audio."""

    speaker: SpeakerRole
    audio_bytes: bytes
    duration_seconds: float
    text: str


@dataclass
class ChapterMarker:
    """A chapter marker in the final audio."""

    title: str
    start_time_ms: int
    end_time_ms: int


@dataclass
class GeneratedPodcast:
    """A complete generated podcast from a paper."""

    paper_metadata: PaperMetadata
    audio_path: Path
    chapters: list[ChapterMarker]
    duration_seconds: float
    persona_type: PersonaType
