"""Shared dataclasses and enums for Peripatos Core."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ArchetypeId(str, Enum):
    PEER = "peer"
    SKEPTIC = "skeptic"
    TUTOR = "tutor"
    ENTHUSIAST = "enthusiast"


@dataclass
class DialogueTurn:
    speaker: str
    text: str
    archetype: ArchetypeId


@dataclass
class DialogueScript:
    title: str
    turns: list[DialogueTurn] = field(default_factory=list)


@dataclass
class AudioSegment:
    speaker: str
    text: str
    audio_path: Path
    duration_s: float


@dataclass
class ChapterMark:
    title: str
    start_ms: int
    end_ms: int


@dataclass
class PaperMetadata:
    title: str
    authors: list[str] = field(default_factory=list)
    abstract: str = ""
    arxiv_id: str | None = None
    source_url: str | None = None
