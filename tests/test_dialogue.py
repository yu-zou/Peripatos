"""Tests for DialogueGenerator."""
from __future__ import annotations

from unittest.mock import Mock, patch

import numpy as np  # pyright: ignore[reportMissingImports]

from peripatos_core.config import Settings
from peripatos_core.dialogue import DialogueGenerator
from peripatos_core.providers.llm import AgentMessage, ToolCall
from peripatos_core.providers.llm_stub import StubLLMProvider
from peripatos_core.types import ArchetypeId, DialogueScript, PaperMetadata


class CyclingStubLLMProvider(StubLLMProvider):
    def __init__(self) -> None:
        super().__init__()
        self._tool_responses = [
            AgentMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id="1",
                        name="draft_turn",
                        arguments={"speaker": "Host", "text": "Hello"},
                    )
                ],
            ),
            AgentMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(id="2", name="finalize", arguments={"title": "Test"})
                ],
            ),
            AgentMessage(role="assistant", content="done", tool_calls=None),
        ]
        self.tool_calls: list[list[AgentMessage]] = []

    def complete_with_tools(self, messages, tools):  # noqa: ANN001, ANN201
        self.tool_calls.append(list(messages))
        return self._tool_responses.pop(0)


def _generate_with_mocks(
    *,
    paper_content: str = "Some paper content",
    archetype: ArchetypeId | str = ArchetypeId.PEER,
    title: str = "Untitled Paper",
    metadata: PaperMetadata | None = None,
) -> tuple[DialogueScript, CyclingStubLLMProvider, Mock, Mock]:
    stub = CyclingStubLLMProvider()
    embedder = Mock()
    embedder.embed.return_value = np.zeros((1, 4), dtype=np.float32)
    store = Mock()
    store.has_cache.return_value = True
    store.load.return_value = None
    store.list_sections.return_value = []
    store.search.return_value = []

    with (
        patch("peripatos_core.dialogue.Embedder", return_value=embedder),
        patch("peripatos_core.dialogue.VectorStore", return_value=store),
    ):
        script = DialogueGenerator(llm=stub, settings=Settings()).generate(
            paper_content,
            archetype=archetype,
            title=title,
            metadata=metadata,
        )

    return script, stub, embedder, store


def test_generate_returns_dialogue_script():
    script, _, _, store = _generate_with_mocks()

    assert isinstance(script, DialogueScript)
    assert script.title == "Test"
    assert len(script.turns) == 1
    assert script.turns[0].speaker == "Host"
    assert script.turns[0].text == "Hello"
    assert script.turns[0].archetype == ArchetypeId.PEER
    store.load.assert_called_once_with()


def test_generate_uses_react_system_prompt():
    metadata = PaperMetadata(title="Paper Title", source_url="https://example.test/paper")
    _, stub, _, _ = _generate_with_mocks(
        paper_content="content",
        title="Fallback Title",
        metadata=metadata,
    )

    initial_messages = stub.tool_calls[0]
    assert initial_messages[0].role == "system"
    assert "Paper Title" in (initial_messages[0].content or "")
    assert "https://example.test/paper" in (initial_messages[0].content or "")
    assert initial_messages[1].role == "user"


def test_generate_by_string_archetype():
    script, _, _, _ = _generate_with_mocks(archetype="tutor")

    assert isinstance(script, DialogueScript)
    assert script.turns[0].archetype == ArchetypeId.TUTOR


def test_generate_builds_vector_store_when_cache_missing():
    stub = CyclingStubLLMProvider()
    embedder = Mock()
    embedder.embed.return_value = np.zeros((1, 4), dtype=np.float32)
    store = Mock()
    store.has_cache.return_value = False
    store.list_sections.return_value = []

    with (
        patch("peripatos_core.dialogue.Embedder", return_value=embedder),
        patch("peripatos_core.dialogue.VectorStore", return_value=store),
    ):
        script = DialogueGenerator(llm=stub, settings=Settings()).generate(
            "# Intro\n\nSome paper content"
        )

    assert script.title == "Test"
    embedder.embed.assert_called_once_with(["# Intro\n\nSome paper content"])
    store.build.assert_called_once()
    store.load.assert_not_called()
