"""Tests for DialogueGenerator."""
from __future__ import annotations

import json
from unittest.mock import Mock, patch

import numpy as np  # pyright: ignore[reportMissingImports]
import pytest

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


class PipelineStubLLMProvider(StubLLMProvider):
    def __init__(self) -> None:
        super().__init__()
        self.complete_calls: list[tuple[str, str]] = []
        self.tool_calls: list[list[AgentMessage]] = []
        self._tool_response_count = 0

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.complete_calls.append((system_prompt, user_prompt))
        if "intro turns" in system_prompt:
            return INTRO_JSON
        if "outro turns" in system_prompt:
            return OUTRO_JSON
        if "planning interview chapters" in system_prompt:
            return VALID_CHAPTERS_JSON
        return "A smooth bridge into the next chapter."

    def complete_with_tools(self, messages, tools):  # noqa: ANN001, ANN201
        self.tool_calls.append(list(messages))
        self._tool_response_count += 1
        if self._tool_response_count % 2 == 1:
            turn_no = (self._tool_response_count + 1) // 2
            return AgentMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id=f"draft-{turn_no}",
                        name="draft_turn",
                        arguments={
                            "speaker": "Host",
                            "text": f"Content-based answer {turn_no}",
                        },
                    )
                ],
            )
        return AgentMessage(
            role="assistant",
            content=None,
            tool_calls=[
                ToolCall(
                    id=f"finalize-{self._tool_response_count // 2}",
                    name="finalize",
                    arguments={"title": "Ignored Agent Title"},
                )
            ],
        )


def _generate_with_mocks(
    *,
    paper_content: str = "Some paper content",
    archetype: ArchetypeId | str = ArchetypeId.PEER,
    title: str = "Untitled Paper",
    metadata: PaperMetadata | None = None,
) -> tuple[DialogueScript, PipelineStubLLMProvider, Mock, Mock]:
    stub = PipelineStubLLMProvider()
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


def test_generate_returns_chaptered_script():
    script, _, _, store = _generate_with_mocks()

    assert isinstance(script, DialogueScript)
    assert script.title == "Untitled Paper"
    assert isinstance(script.chapters, list)
    assert 3 <= len(script.chapters) <= 7
    assert all(isinstance(chapter, Chapter) for chapter in script.chapters)
    assert all(chapter.turns for chapter in script.chapters)
    store.load.assert_called_once_with()


def test_generate_chapter_titles_content_based():
    script, _, _, _ = _generate_with_mocks()

    assert script.chapters[0].title == "Introduction"
    assert script.chapters[0].title not in {"Host", "Guest", "Peer", "Tutor"}


def test_generate_transitions_populated():
    script, _, _, _ = _generate_with_mocks()

    assert script.chapters[0].transition_in_text is None
    assert script.chapters[1].transition_in_text is not None
    assert script.chapters[2].transition_in_text is not None


def test_generate_turns_deprecated():
    script, _, _, _ = _generate_with_mocks()

    with pytest.warns(DeprecationWarning):
        turns = script.turns

    assert turns == [turn for chapter in script.chapters for turn in chapter.turns]
    assert len(turns) == 6


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
    assert "Answer this question" in (initial_messages[1].content or "")


def test_generate_by_string_archetype():
    script, _, _, _ = _generate_with_mocks(archetype="tutor")

    assert isinstance(script, DialogueScript)
    with pytest.warns(DeprecationWarning):
        turns = script.turns
    assert turns[0].archetype == ArchetypeId.TUTOR


def test_generate_builds_vector_store_when_cache_missing():
    stub = PipelineStubLLMProvider()
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

    assert script.title == "Untitled Paper"
    embedder.embed.assert_called_once_with(["# Intro\n\nSome paper content"])
    store.build.assert_called_once()
    store.load.assert_not_called()


# ---------------------------------------------------------------------------
# Phase A parser tests
# ---------------------------------------------------------------------------

INTRO_JSON = json.dumps([
    {"speaker": "Host", "text": "Welcome to the podcast! Today we explore a fascinating paper."},
    {"speaker": "Host", "text": "Let me introduce our guest expert who will walk us through the key ideas."},
])

OUTRO_JSON = json.dumps([
    {"speaker": "Host", "text": "That wraps up our discussion. Thanks for joining us today."},
    {"speaker": "Host", "text": "Join us next time for more cutting-edge research."},
])

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


# ---------------------------------------------------------------------------
# Language instruction injection tests
# ---------------------------------------------------------------------------


def test_language_instruction_zh_CN_passed_to_react_system():
    """With language='zh-CN', load_react_system receives Mandarin instruction."""
    from peripatos_core.prompts import load_react_system as _real_load

    captured_kwargs: dict = {}

    def _capture_load(*args, **kwargs):  # noqa: ANN202
        captured_kwargs.clear()
        captured_kwargs.update(kwargs)
        return _real_load(*args, **kwargs)

    stub = PipelineStubLLMProvider()
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
        patch("peripatos_core.dialogue.load_react_system", side_effect=_capture_load),
    ):
        settings = Settings(language="zh-CN")
        DialogueGenerator(llm=stub, settings=settings).generate("Some paper content")

    assert "language_instruction" in captured_kwargs, (
        f"load_react_system kwargs: {list(captured_kwargs.keys())}"
    )
    assert "Mandarin" in captured_kwargs["language_instruction"]


def test_language_instruction_en_in_phase_a_prompt():
    """With language='en', Phase A user prompt contains 'Respond in English'."""
    script, stub, _, _ = _generate_with_mocks()

    assert isinstance(script, DialogueScript)
    # First complete call is intro; Phase A is the second complete call
    phase_a_user_prompt = stub.complete_calls[1][1]
    assert "Respond in English" in phase_a_user_prompt


# ---------------------------------------------------------------------------
# Intro / Outro generation tests
# ---------------------------------------------------------------------------


def test_generate_includes_intro_turns():
    script, _, _, _ = _generate_with_mocks()

    assert isinstance(script.intro_turns, list)
    assert len(script.intro_turns) == 2
    assert all(isinstance(t, DialogueTurn) for t in script.intro_turns)
    assert script.intro_turns[0].speaker == "Host"
    assert "welcome" in script.intro_turns[0].text.lower()


def test_generate_includes_outro_turns():
    script, _, _, _ = _generate_with_mocks()

    assert isinstance(script.outro_turns, list)
    assert len(script.outro_turns) == 2
    assert all(isinstance(t, DialogueTurn) for t in script.outro_turns)
    assert script.outro_turns[0].speaker == "Host"
    assert "thanks" in script.outro_turns[0].text.lower()


def test_intro_turns_appear_before_chapters():
    script, _, _, _ = _generate_with_mocks()

    assert len(script.intro_turns) > 0
    assert len(script.chapters) > 0
    assert script.chapters[0].turns[0].text not in {t.text for t in script.intro_turns}


def test_outro_turns_appear_after_chapters():
    script, _, _, _ = _generate_with_mocks()

    assert len(script.outro_turns) > 0
    last_chapter_turns = {t.text for c in script.chapters for t in c.turns}
    for outro_turn in script.outro_turns:
        assert outro_turn.text not in last_chapter_turns


def test_intro_llm_call_has_correct_system_prompt():
    _, stub, _, _ = _generate_with_mocks()

    intro_system, intro_user = stub.complete_calls[0]
    assert "intro turns" in intro_system
    assert "Untitled Paper" in intro_user
    assert "unknown" in intro_user


def test_outro_llm_call_has_correct_system_prompt():
    _, stub, _, _ = _generate_with_mocks()

    outro_system, outro_user = stub.complete_calls[-1]
    assert "outro turns" in outro_system
    assert "Untitled Paper" in outro_user


# ---------------------------------------------------------------------------
# _parse_turns_json tests
# ---------------------------------------------------------------------------


def test_parse_turns_json_valid():
    from peripatos_core.dialogue import DialogueGenerator

    raw = json.dumps([
        {"speaker": "Host", "text": "Hello and welcome!"},
        {"speaker": "Host", "text": "Today we discuss transformers."},
    ])
    result = DialogueGenerator._parse_turns_json(raw, ArchetypeId.PEER)

    assert len(result) == 2
    assert result[0].speaker == "Host"
    assert result[0].text == "Hello and welcome!"
    assert result[0].archetype == ArchetypeId.PEER
    assert result[1].speaker == "Host"
    assert result[1].text == "Today we discuss transformers."


def test_parse_turns_json_invalid_json():
    from peripatos_core.dialogue import DialogueGenerator

    result = DialogueGenerator._parse_turns_json("not json", ArchetypeId.PEER)
    assert result == []


def test_parse_turns_json_non_list():
    from peripatos_core.dialogue import DialogueGenerator

    result = DialogueGenerator._parse_turns_json('{"key": "value"}', ArchetypeId.PEER)
    assert result == []


def test_parse_turns_json_skips_invalid_items():
    from peripatos_core.dialogue import DialogueGenerator

    raw = json.dumps([
        {"speaker": "Host", "text": "Valid turn."},
        "not a dict",
        {"speaker": "Host", "text": ""},
        {"no_text_here": True},
    ])
    result = DialogueGenerator._parse_turns_json(raw, ArchetypeId.TUTOR)

    assert len(result) == 1
    assert result[0].text == "Valid turn."
    assert result[0].archetype == ArchetypeId.TUTOR


def test_parse_turns_json_default_speaker():
    from peripatos_core.dialogue import DialogueGenerator

    raw = json.dumps([
        {"text": "Turn with no explicit speaker."},
    ])
    result = DialogueGenerator._parse_turns_json(raw, ArchetypeId.PEER)
    assert len(result) == 1
    assert result[0].speaker == "Host"


# ---------------------------------------------------------------------------
# target_turns pacing tests
# ---------------------------------------------------------------------------


def test_target_turns_passed_to_react_system():
    """Verify that _calculate_target_turns output is passed to load_react_system."""
    from peripatos_core.prompts import load_react_system as _real_load

    captured_kwargs: dict = {}

    def _capture_load(*args, **kwargs):
        captured_kwargs.clear()
        captured_kwargs.update(kwargs)
        return _real_load(*args, **kwargs)

    stub = PipelineStubLLMProvider()
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
        patch("peripatos_core.dialogue.load_react_system", side_effect=_capture_load),
    ):
        DialogueGenerator(llm=stub, settings=Settings()).generate(
            "# Title\n\nThis is a short paper.\n"
        )

    assert "target_turns" in captured_kwargs
    target = captured_kwargs["target_turns"]
    # 7 words / 300 * 2 = 0.04 → floor → 0, clamped to min 10
    assert target == "10"


def test_target_turns_scales_with_paper_length():
    """Longer paper → higher target_turns."""
    from peripatos_core.prompts import load_react_system as _real_load

    captured_kwargs: dict = {}

    def _capture_load(*args, **kwargs):
        captured_kwargs.clear()
        captured_kwargs.update(kwargs)
        return _real_load(*args, **kwargs)

    stub = PipelineStubLLMProvider()
    embedder = Mock()
    embedder.embed.return_value = np.zeros((1, 4), dtype=np.float32)
    store = Mock()
    store.has_cache.return_value = True
    store.load.return_value = None
    store.list_sections.return_value = []
    store.search.return_value = []

    long_content = " ".join(["word"] * 6000)

    with (
        patch("peripatos_core.dialogue.Embedder", return_value=embedder),
        patch("peripatos_core.dialogue.VectorStore", return_value=store),
        patch("peripatos_core.dialogue.load_react_system", side_effect=_capture_load),
    ):
        DialogueGenerator(llm=stub, settings=Settings()).generate(long_content)

    assert "target_turns" in captured_kwargs
    # 6000 words / 300 * 2 = 40 → max 40
    assert captured_kwargs["target_turns"] == "40"


# ---------------------------------------------------------------------------
# Task 2: JSON-wrapped transition / LaTeX parsing
# ---------------------------------------------------------------------------


def test_phase_c_parses_json_transition():
    """Transition text wrapped in JSON object should be extracted."""
    llm = Mock(spec=LLMProvider)
    llm.complete.return_value = '{"transition": "Now let\'s move to the next topic."}'
    gen = DialogueGenerator(llm=llm, settings=Settings())

    chapters = [
        Chapter(title="Ch1", turns=[DialogueTurn(speaker="Host", text="Hello", archetype=ArchetypeId.PEER)]),
        Chapter(title="Ch2", turns=[DialogueTurn(speaker="Guest", text="Hi", archetype=ArchetypeId.PEER)]),
    ]

    result = gen._run_phase_c(chapters)
    assert result[1].transition_in_text == "Now let's move to the next topic."
    assert not result[1].transition_in_text.startswith("{")


def test_phase_c_parses_json_latex():
    """LaTeX conversion wrapped in JSON object should be extracted."""
    llm = Mock(spec=LLMProvider)
    llm.complete.side_effect = [
        "A smooth transition.",
        '{"text": "x squared equals the sum of squares"}',
    ]
    gen = DialogueGenerator(llm=llm, settings=Settings())

    chapters = [
        Chapter(title="Ch1", turns=[DialogueTurn(speaker="Host", text="Hello", archetype=ArchetypeId.PEER)]),
        Chapter(
            title="Ch2",
            turns=[DialogueTurn(speaker="Host", text="Consider $x^2$ for this.", archetype=ArchetypeId.PEER)],
        ),
    ]

    result = gen._run_phase_c(chapters)
    assert result[1].turns[0].text == "x squared equals the sum of squares"
    assert not result[1].turns[0].text.startswith("{")


# ---------------------------------------------------------------------------
# Task 3: Intro/outro host_name consistency tests
# ---------------------------------------------------------------------------


def test_intro_prompt_includes_host_name():
    """Intro prompt template should include {host_name} and it should be replaced."""
    _, stub, _, _ = _generate_with_mocks()
    intro_system, intro_user = stub.complete_calls[0]
    assert "{host_name}" not in intro_user, "Template placeholder {host_name} should be replaced"
    assert "Alex" in intro_user


def test_outro_prompt_includes_host_name():
    """Outro prompt template should include {host_name} and it should be replaced."""
    _, stub, _, _ = _generate_with_mocks()
    outro_system, outro_user = stub.complete_calls[-1]
    assert "{host_name}" not in outro_user, "Template placeholder {host_name} should be replaced"
    assert "Alex" in outro_user
