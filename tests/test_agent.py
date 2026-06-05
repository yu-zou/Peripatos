import pytest
from typing import Any, cast

from peripatos_core.exceptions import AgentError
from peripatos_core.providers.llm import AgentMessage, ToolCall, ToolSpec
from peripatos_core.providers.llm_stub import StubLLMProvider
from peripatos_core.rag.agent import MAX_ITERATIONS, ReActAgent, run_agent
from peripatos_core.types import DialogueScript


class CyclingStubLLMProvider(StubLLMProvider):
    def __init__(self, responses: list[AgentMessage]) -> None:
        super().__init__()
        self._responses = responses
        self.tool_calls_seen = 0
        self.messages_seen: list[list[AgentMessage]] = []

    def complete_with_tools(
        self,
        messages: list[AgentMessage],
        tools: list[ToolSpec],
    ) -> AgentMessage:
        self.messages_seen.append(list(messages))
        response = self._responses[min(self.tool_calls_seen, len(self._responses) - 1)]
        self.tool_calls_seen += 1
        return response


class EmptyStore:
    def search(self, _embedding, _k: int):
        return []

    def get_chunk(self, _chunk_id: int):
        return {"text": ""}

    def list_sections(self):
        return []


class TrackingStore(EmptyStore):
    def __init__(self) -> None:
        self.search_queries: list[Any] = []

    def search(self, embedding, k: int):
        self.search_queries.append((embedding, k))
        return [(1, 0.1, "grounded chunk")]


class EmptyEmbedder:
    def embed(self, _texts: list[str]):
        return [[0.0]]


def make_agent(llm: StubLLMProvider) -> ReActAgent:
    return ReActAgent(
        llm=llm,
        store=cast(Any, EmptyStore()),
        embedder=cast(Any, EmptyEmbedder()),
        top_k=3,
    )


def draft_call(call_id: str, speaker: str, text: str) -> ToolCall:
    return ToolCall(
        id=call_id,
        name="draft_turn",
        arguments={"speaker": speaker, "text": text},
    )


def finalize_call(call_id: str, title: str = "Test Paper") -> ToolCall:
    return ToolCall(id=call_id, name="finalize", arguments={"title": title})


def test_react_agent_happy_path():
    llm = CyclingStubLLMProvider(
        [
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
                    ToolCall(
                        id="2",
                        name="finalize",
                        arguments={"title": "Test Paper"},
                    )
                ],
            ),
            AgentMessage(role="assistant", content="done", tool_calls=None),
        ]
    )
    agent = make_agent(llm)

    script = agent.run("system", "user")

    assert isinstance(script, DialogueScript)
    assert script.title == "Test Paper"
    assert len(script.chapters[0].turns) == 1
    assert script.chapters[0].turns[0].speaker == "Host"
    assert script.chapters[0].turns[0].text == "Hello"
    assert llm.tool_calls_seen == 2


def test_react_agent_iteration_cap_warns_and_returns_partial_script():
    llm = CyclingStubLLMProvider(
        [
            AgentMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id="draft",
                        name="draft_turn",
                        arguments={"speaker": "Host", "text": "Still drafting"},
                    )
                ],
            )
        ]
    )
    agent = make_agent(llm)

    with pytest.warns(UserWarning, match=r"ReAct iteration cap reached \(80\)"):
        script = agent.run("system", "user")

    assert script.title == "Untitled"
    assert len(script.chapters[0].turns) == MAX_ITERATIONS
    assert llm.tool_calls_seen == MAX_ITERATIONS


def test_react_agent_empty_turns_raises_agent_error():
    llm = CyclingStubLLMProvider(
        [
            AgentMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id="1",
                        name="finalize",
                        arguments={"title": "Empty"},
                    )
                ],
            )
        ]
    )
    agent = make_agent(llm)

    with pytest.raises(AgentError, match="agent produced no turns"):
        agent.run("system", "user")


def test_per_question_two_questions():
    llm = CyclingStubLLMProvider(
        [
            AgentMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    draft_call("q1-1", "Host", "Question one setup"),
                    draft_call("q1-2", "Guest", "Question one answer"),
                    finalize_call("q1-final"),
                ],
            ),
            AgentMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    draft_call("q2-1", "Host", "Question two setup"),
                    draft_call("q2-2", "Guest", "Question two answer"),
                    finalize_call("q2-final"),
                ],
            ),
        ]
    )

    result = run_agent(
        llm=llm,
        store=cast(Any, EmptyStore()),
        embedder=cast(Any, EmptyEmbedder()),
        questions=["What is alpha?", "What is beta?"],
        system_prompt="system {question} {chapter_title}",
        chapter_title="Chapter A",
        top_k=3,
    )

    assert len(result) == 2
    assert [turn.text for turn in result[0]] == [
        "Question one setup",
        "Question one answer",
    ]
    assert [turn.text for turn in result[1]] == [
        "Question two setup",
        "Question two answer",
    ]
    assert "What is alpha?" in (llm.messages_seen[0][0].content or "")
    assert "Chapter A" in (llm.messages_seen[0][0].content or "")
    assert "What is beta?" in (llm.messages_seen[1][1].content or "")


def test_per_question_replaces_real_prompt_placeholders():
    llm = CyclingStubLLMProvider(
        [
            AgentMessage(
                role="assistant",
                content=None,
                tool_calls=[draft_call("draft", "Host", "Focused answer")],
            )
        ]
    )

    result = run_agent(
        llm=llm,
        store=cast(Any, EmptyStore()),
        embedder=cast(Any, EmptyEmbedder()),
        questions=["What is alpha?"],
        system_prompt="Chapter: {{chapter_title}}\nQuestion: {{question}}",
        chapter_title="Chapter A",
        top_k=3,
    )

    system_message = llm.messages_seen[0][0].content or ""
    assert len(result) == 1
    assert result[0][0].text == "Focused answer"
    assert "Chapter: Chapter A" in system_message
    assert "Question: What is alpha?" in system_message
    assert "{chapter_title}" not in system_message
    assert "{question}" not in system_message


def test_legacy_run_agent_strips_focused_placeholders():
    llm = CyclingStubLLMProvider(
        [
            AgentMessage(
                role="assistant",
                content=None,
                tool_calls=[draft_call("draft", "Host", "Legacy answer")],
            ),
            AgentMessage(
                role="assistant",
                content=None,
                tool_calls=[finalize_call("final")],
            ),
        ]
    )

    result = run_agent(
        llm=llm,
        store=cast(Any, EmptyStore()),
        embedder=cast(Any, EmptyEmbedder()),
        system_prompt="Chapter: {chapter_title}\nQuestion: {question}",
        user_prompt="legacy user prompt",
        top_k=3,
    )

    system_message = llm.messages_seen[0][0].content or ""
    assert isinstance(result, DialogueScript)
    assert result.chapters[0].turns[0].text == "Legacy answer"
    assert "{chapter_title}" not in system_message
    assert "{question}" not in system_message


def test_per_question_grounding():
    llm = CyclingStubLLMProvider(
        [
            AgentMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    ToolCall(
                        id="search-1",
                        name="search",
                        arguments={"query": "mechanism"},
                    ),
                ],
            ),
            AgentMessage(
                role="assistant",
                content=None,
                tool_calls=[draft_call("draft-1", "Guest", "Grounded answer")],
            ),
        ]
    )
    store = TrackingStore()

    result = run_agent(
        llm=llm,
        store=cast(Any, store),
        embedder=cast(Any, EmptyEmbedder()),
        questions=["How does it work?"],
        system_prompt="system",
        top_k=3,
    )

    assert len(result) == 1
    assert result[0][0].text == "Grounded answer"
    assert store.search_queries == [([0.0], 3)]


def test_per_question_max_turns():
    llm = CyclingStubLLMProvider(
        [
            AgentMessage(
                role="assistant",
                content=None,
                tool_calls=[
                    draft_call(str(index), "Host", f"Turn {index}")
                    for index in range(1, 8)
                ],
            )
        ]
    )

    result = run_agent(
        llm=llm,
        store=cast(Any, EmptyStore()),
        embedder=cast(Any, EmptyEmbedder()),
        questions=["What is capped?"],
        system_prompt="system",
        top_k=3,
    )

    assert len(result) == 1
    assert [turn.text for turn in result[0]] == [
        "Turn 1",
        "Turn 2",
        "Turn 3",
        "Turn 4",
        "Turn 5",
    ]
