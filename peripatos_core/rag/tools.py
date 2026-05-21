"""Agent tool definitions."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from peripatos_core.providers.llm import ToolSpec
from peripatos_core.types import ArchetypeId, DialogueTurn

if TYPE_CHECKING:
    from peripatos_core.rag.embedder import Embedder
    from peripatos_core.rag.vector_store import VectorStore


@dataclass
class AgentState:
    drafted_turns: list[DialogueTurn] = field(default_factory=list)
    title: str | None = None
    finalized: bool = False


def build_tools(
    store: "VectorStore",
    embedder: "Embedder",
    top_k: int,
    archetype: ArchetypeId = ArchetypeId.PEER,
) -> tuple[list[ToolSpec], dict[str, Callable], AgentState]:
    state = AgentState()

    def search(query: str) -> str:
        embedding = embedder.embed([query])[0]
        results = store.search(embedding, k=top_k)
        return json.dumps(
            [
                {"id": chunk_id, "text": text, "distance": distance}
                for chunk_id, distance, text in results
            ]
        )

    def read_chunk(chunk_id: int) -> str:
        entry = store.get_chunk(chunk_id)
        return entry["text"]

    def list_sections() -> str:
        sections = store.list_sections()
        return json.dumps(
            [{"id": chunk_id, "section_hint": hint} for chunk_id, hint in sections]
        )

    def draft_turn(speaker: str, text: str) -> str:
        state.drafted_turns.append(
            DialogueTurn(speaker=speaker, text=text, archetype=archetype)
        )
        return f"ok, {len(state.drafted_turns)} turns drafted so far"

    def finalize(title: str) -> str:
        state.title = title
        state.finalized = True
        return "finalized"

    def _wrap(fn):
        def handler(**kwargs):
            return fn(**kwargs)
        return handler

    specs: list[ToolSpec] = [
        ToolSpec(
            name="search",
            description="Search the paper for relevant chunks via semantic similarity.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"],
            },
        ),
        ToolSpec(
            name="read_chunk",
            description="Read the full text of a chunk by its ID.",
            parameters={
                "type": "object",
                "properties": {
                    "chunk_id": {"type": "integer", "description": "Chunk ID to read"}
                },
                "required": ["chunk_id"],
            },
        ),
        ToolSpec(
            name="list_sections",
            description="List the sections discovered in the paper.",
            parameters={"type": "object", "properties": {}},
        ),
        ToolSpec(
            name="draft_turn",
            description="Draft one dialogue turn (speaker + text). Accumulates across calls.",
            parameters={
                "type": "object",
                "properties": {
                    "speaker": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["speaker", "text"],
            },
        ),
        ToolSpec(
            name="finalize",
            description="Finalize the dialogue with a title.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Dialogue title"}
                },
                "required": ["title"],
            },
        ),
    ]

    dispatcher: dict[str, Callable] = {
        "search": _wrap(search),
        "read_chunk": _wrap(read_chunk),
        "list_sections": _wrap(list_sections),
        "draft_turn": _wrap(draft_turn),
        "finalize": _wrap(finalize),
    }

    return specs, dispatcher, state


__all__ = ["AgentState", "build_tools"]
