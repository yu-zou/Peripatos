"""Tests for DialogueGenerator."""
from __future__ import annotations

import json
from unittest.mock import Mock, patch

import numpy as np  # pyright: ignore[reportMissingImports]

from peripatos_core.config import Settings
from peripatos_core.dialogue import (
    DialogueGenerator,
    _FALLBACK_CHAPTERS,
    _contains_latex,
    _parse_phase_a_output,
)
from peripatos_core.providers.llm import AgentMessage, LLMProvider, ToolCall
from peripatos_core.providers.llm_stub import StubLLMProvider
from peripatos_core.types import ArchetypeId, Chapter, DialogueScript, DialogueTurn, PaperMetadata


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


# ---------------------------------------------------------------------------
# Phase A parser tests
# ---------------------------------------------------------------------------

VALID_CHAPTERS_JSON = json.dumps({
    "chapters": [
        {"title": "Introduction", "questions": ["q1", "q2"]},
        {"title": "Background", "questions": ["q3", "q4"]},
        {"title": "Methodology", "questions": ["q5", "q6"]},
    ]
})

TWO_CHAPTERS_JSON = json.dumps({
    "chapters": [
        {"title": "A", "questions": ["q1", "q2"]},
        {"title": "B", "questions": ["q3", "q4"]},
    ]
})

EIGHT_CHAPTERS_JSON = json.dumps({
    "chapters": [
        {"title": f"Ch{i}", "questions": ["q1", "q2"]}
        for i in range(1, 9)
    ]
})

ONE_QUESTION_JSON = json.dumps({
    "chapters": [
        {"title": "A", "questions": ["q1"]},
        {"title": "B", "questions": ["q2"]},
        {"title": "C", "questions": ["q3"]},
    ]
})

SIX_QUESTIONS_JSON = json.dumps({
    "chapters": [
        {"title": "A", "questions": [f"q{i}" for i in range(1, 7)]},
        {"title": "B", "questions": ["q1", "q2"]},
        {"title": "C", "questions": ["q3", "q4"]},
    ]
})


def test_valid_phase_a_output():
    """Valid JSON with 3 chapters, 2 questions each → 3 chapters returned."""
    result = _parse_phase_a_output(VALID_CHAPTERS_JSON)
    assert len(result) == 3
    assert result[0]["title"] == "Introduction"
    assert result[0]["questions"] == ["q1", "q2"]


def test_phase_a_invalid_json():
    """Non-JSON string → returns FALLBACK_CHAPTERS."""
    result = _parse_phase_a_output("not json")
    assert result is _FALLBACK_CHAPTERS
    assert len(result) == 5


def test_phase_a_too_few_chapters():
    """2 chapters → returns FALLBACK_CHAPTERS."""
    result = _parse_phase_a_output(TWO_CHAPTERS_JSON)
    assert result is _FALLBACK_CHAPTERS


def test_phase_a_too_many_chapters():
    """8 chapters → returns FALLBACK_CHAPTERS."""
    result = _parse_phase_a_output(EIGHT_CHAPTERS_JSON)
    assert result is _FALLBACK_CHAPTERS


def test_phase_a_too_few_questions():
    """Chapter with 1 question → returns FALLBACK_CHAPTERS."""
    result = _parse_phase_a_output(ONE_QUESTION_JSON)
    assert result is _FALLBACK_CHAPTERS


def test_phase_a_too_many_questions():
    """Chapter with 6 questions → returns FALLBACK_CHAPTERS."""
    result = _parse_phase_a_output(SIX_QUESTIONS_JSON)
    assert result is _FALLBACK_CHAPTERS


def test_phase_a_title_too_long():
    """Title > 80 chars → returns FALLBACK_CHAPTERS."""
    long_title = "A" * 81
    data = json.dumps({
        "chapters": [
            {"title": long_title, "questions": ["q1", "q2"]},
            {"title": "B", "questions": ["q3", "q4"]},
            {"title": "C", "questions": ["q5", "q6"]},
        ]
    })
    result = _parse_phase_a_output(data)
    assert result is _FALLBACK_CHAPTERS


# ---------------------------------------------------------------------------
# Phase A _run_phase_a integration tests
# ---------------------------------------------------------------------------


def _make_dialogue_generator(llm_complete_returns: list[str] | Mock) -> DialogueGenerator:
    """Create a DialogueGenerator whose _llm.complete is pre-configured."""
    llm_mock = Mock(spec=LLMProvider)
    if isinstance(llm_complete_returns, list):
        llm_mock.complete.side_effect = list(llm_complete_returns)
    else:
        llm_mock.complete = llm_complete_returns
    return DialogueGenerator(llm=llm_mock, settings=Settings())


def test_run_phase_a_success():
    """Mock LLM returns valid JSON → returns validated chapters (not fallback)."""
    gen = _make_dialogue_generator([VALID_CHAPTERS_JSON])
    result = gen._run_phase_a(
        archetype_system_prompt="Be a peer.",
        title="Test Paper",
        origin="test",
        section_overview="Sections...",
    )
    assert result is not _FALLBACK_CHAPTERS
    assert len(result) == 3
    assert result[0]["title"] == "Introduction"


def test_run_phase_a_retries():
    """Mock returning invalid twice, valid on 3rd call → valid chapters, 3 calls."""
    gen = _make_dialogue_generator(["not json", "still not json", VALID_CHAPTERS_JSON])
    result = gen._run_phase_a(
        archetype_system_prompt="Be a peer.",
        title="Test Paper",
        origin="test",
        section_overview="Sections...",
    )
    assert result is not _FALLBACK_CHAPTERS
    assert len(result) == 3
    assert gen._llm.complete.call_count == 3  # type: ignore[union-attr]


def test_run_phase_a_exhausted():
    """Mock returning invalid 3 times → returns FALLBACK_CHAPTERS, 3 calls."""
    gen = _make_dialogue_generator(["not json", "still not", "no"])
    result = gen._run_phase_a(
        archetype_system_prompt="Be a peer.",
        title="Test Paper",
        origin="test",
        section_overview="Sections...",
    )
    assert result is _FALLBACK_CHAPTERS
    assert gen._llm.complete.call_count == 3  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# _contains_latex tests
# ---------------------------------------------------------------------------


def test_contains_latex_dollar():
    assert _contains_latex("$x^2$") is True


def test_contains_latex_no_math():
    assert _contains_latex("no math here") is False


def test_contains_latex_frac():
    assert _contains_latex(r"\frac{a}{b}") is True


# ---------------------------------------------------------------------------
# Phase C _run_phase_c tests
# ---------------------------------------------------------------------------


def test_run_phase_c_transitions():
    """Mock LLM returning a transition → chapter 1 gets transition_in_text, chapter 0 stays None."""
    llm = Mock(spec=LLMProvider)
    llm.complete.return_value = "Now let's discuss Methods."
    gen = DialogueGenerator(llm=llm, settings=Settings())

    chapters = [
        Chapter(title="Introduction", turns=[DialogueTurn(speaker="Host", text="Today we explore AI.", archetype=ArchetypeId.PEER)]),
        Chapter(title="Methods", turns=[DialogueTurn(speaker="Host", text="Let me explain the model.", archetype=ArchetypeId.PEER)]),
        Chapter(title="Results", turns=[DialogueTurn(speaker="Host", text="Here are the numbers.", archetype=ArchetypeId.PEER)]),
    ]

    result = gen._run_phase_c(chapters)

    assert result[0].transition_in_text is None
    assert result[1].transition_in_text == "Now let's discuss Methods."
    assert result[2].transition_in_text == "Now let's discuss Methods."
    assert llm.complete.call_count == 2


def test_run_phase_c_latex_conversion():
    """Mock LLM converting LaTeX → turn.text no longer contains $ after conversion."""
    llm = Mock(spec=LLMProvider)
    llm.complete.return_value = "x squared expression"

    gen = DialogueGenerator(llm=llm, settings=Settings())
    chapters = [
        Chapter(
            title="Math Intro",
            turns=[DialogueTurn(speaker="Host", text="Consider $x^2$ for this example.", archetype=ArchetypeId.PEER)],
        ),
    ]

    result = gen._run_phase_c(chapters)

    assert "$" not in result[0].turns[0].text
    assert result[0].turns[0].text == "x squared expression"


def test_run_phase_c_transition_truncation():
    """Transition longer than 200 chars → truncated to 200 with ... suffix."""
    llm = Mock(spec=LLMProvider)
    llm.complete.return_value = "X" * 250

    gen = DialogueGenerator(llm=llm, settings=Settings())
    chapters = [
        Chapter(title="Intro", turns=[DialogueTurn(speaker="Host", text="Hello.", archetype=ArchetypeId.PEER)]),
        Chapter(title="Methods", turns=[DialogueTurn(speaker="Host", text="Details.", archetype=ArchetypeId.PEER)]),
    ]

    result = gen._run_phase_c(chapters)

    transition = result[1].transition_in_text or ""
    assert len(transition) <= 200
    assert transition.endswith("...")


def test_run_phase_c_no_latex_unchanged():
    """Turns without LaTeX are left unchanged."""
    llm = Mock(spec=LLMProvider)
    llm.complete.return_value = "some transition"
    gen = DialogueGenerator(llm=llm, settings=Settings())

    original_text = "Just plain English here."
    chapters = [
        Chapter(title="A", turns=[DialogueTurn(speaker="Host", text=original_text, archetype=ArchetypeId.PEER)]),
        Chapter(title="B", turns=[DialogueTurn(speaker="Host", text=original_text, archetype=ArchetypeId.PEER)]),
    ]

    result = gen._run_phase_c(chapters)

    assert result[0].turns[0].text == original_text
    assert result[1].turns[0].text == original_text


def test_run_phase_c_single_chapter_no_transition():
    """Single chapter → no transitions generated (nothing to bridge from)."""
    llm = Mock(spec=LLMProvider)
    gen = DialogueGenerator(llm=llm, settings=Settings())

    chapters = [
        Chapter(title="Only Chapter", turns=[DialogueTurn(speaker="Host", text="Content.", archetype=ArchetypeId.PEER)]),
    ]

    result = gen._run_phase_c(chapters)

    assert result[0].transition_in_text is None
    llm.complete.assert_not_called()
