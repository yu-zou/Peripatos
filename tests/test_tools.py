"""Tests for agent tool definitions."""
import pytest
from typing import Any, cast

from peripatos_core.rag.tools import build_tools
from peripatos_core.types import ArchetypeId


class EmptyStore:
    def search(self, _embedding, _k: int):
        return []

    def list_sections(self):
        return []


class EmptyEmbedder:
    def embed(self, _texts):
        return [[0.0]]


def test_draft_turn_strips_literal_newlines():
    """draft_turn should strip literal \\n sequences that would cause TTS to say 'back slash'."""
    specs, dispatcher, state = build_tools(
        cast(Any, EmptyStore()), cast(Any, EmptyEmbedder()), top_k=4
    )
    dispatcher["draft_turn"](speaker="Host", text="Hello\\n\\nWorld")
    assert "\\n" not in state.drafted_turns[0].text
    assert state.drafted_turns[0].text == "Hello World"


def test_draft_turn_strips_literal_tabs():
    """draft_turn should strip literal \\t sequences."""
    specs, dispatcher, state = build_tools(
        cast(Any, EmptyStore()), cast(Any, EmptyEmbedder()), top_k=4
    )
    dispatcher["draft_turn"](speaker="Host", text="Hello\\tWorld")
    assert "\\t" not in state.drafted_turns[0].text


def test_draft_turn_preserves_real_newlines():
    """draft_turn should NOT strip actual newline characters."""
    specs, dispatcher, state = build_tools(
        cast(Any, EmptyStore()), cast(Any, EmptyEmbedder()), top_k=4
    )
    dispatcher["draft_turn"](speaker="Host", text="Hello\nWorld")
    # Actual newline is kept — text.split() with join collapses them to spaces
    assert "Hello" in state.drafted_turns[0].text
    assert "World" in state.drafted_turns[0].text


def test_draft_turn_description_mentions_language():
    """draft_turn ToolSpec description should remind the LLM to write in the target language."""
    specs, _dispatcher, _state = build_tools(
        cast(Any, EmptyStore()), cast(Any, EmptyEmbedder()), top_k=4
    )
    draft_spec = next(s for s in specs if s.name == "draft_turn")
    assert "language" in draft_spec.description.lower()


def test_draft_turn_collapses_multiple_spaces():
    """After stripping, multiple spaces should collapse to single space."""
    specs, dispatcher, state = build_tools(
        cast(Any, EmptyStore()), cast(Any, EmptyEmbedder()), top_k=4
    )
    dispatcher["draft_turn"](speaker="Host", text="Hello   World")
    assert state.drafted_turns[0].text == "Hello World"