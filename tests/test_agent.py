import pytest
from typing import Any, cast

from peripatos_core.exceptions import AgentError
from peripatos_core.providers.llm import AgentMessage, ToolCall, ToolSpec
from peripatos_core.providers.llm_stub import StubLLMProvider
from peripatos_core.rag.agent import MAX_ITERATIONS, ReActAgent
from peripatos_core.types import DialogueScript


class CyclingStubLLMProvider(StubLLMProvider):
    def __init__(self, responses: list[AgentMessage]) -> None:
        super().__init__()
        self._responses = responses
        self.tool_calls_seen = 0

    def complete_with_tools(
        self,
        messages: list[AgentMessage],
        tools: list[ToolSpec],
    ) -> AgentMessage:
        response = self._responses[min(self.tool_calls_seen, len(self._responses) - 1)]
        self.tool_calls_seen += 1
        return response


class EmptyStore:
    def search(self, embedding, k: int):
        return []

    def get_chunk(self, chunk_id: int):
        return {"text": ""}

    def list_sections(self):
        return []


class EmptyEmbedder:
    def embed(self, texts: list[str]):
        return [[0.0]]


def make_agent(llm: StubLLMProvider) -> ReActAgent:
    return ReActAgent(
        llm=llm,
        store=cast(Any, EmptyStore()),
        embedder=cast(Any, EmptyEmbedder()),
        top_k=3,
    )


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
    assert len(script.turns) == 1
    assert script.turns[0].speaker == "Host"
    assert script.turns[0].text == "Hello"
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
    assert len(script.turns) == MAX_ITERATIONS
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


