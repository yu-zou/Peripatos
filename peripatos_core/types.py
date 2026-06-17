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
class Chapter:
    title: str
    turns: list[DialogueTurn] = field(default_factory=list)
    transition_in_text: str | None = None


@dataclass
class DialogueScript:
    title: str
    chapters: list[Chapter] = field(default_factory=list)
    intro_turns: list[DialogueTurn] = field(default_factory=list)
    outro_turns: list[DialogueTurn] = field(default_factory=list)

    @property
    def turns(self) -> list[DialogueTurn]:
        import warnings

        warnings.warn(
            "DialogueScript.turns is deprecated, use .chapters instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return [turn for chapter in self.chapters for turn in chapter.turns]


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


def _calculate_target_turns(paper_content: str) -> int:
    """Estimate target dialogue turns based on paper length.

    ~300 words per double-column page. Aim for ~1.5 turns per page,
    targeting 10-15 minutes of audio. Min 12 turns, max 30 turns.
    """
    word_count = len(paper_content.split())
    pages = word_count / 300
    target = int(pages * 1.5)
    return max(12, min(30, target))
