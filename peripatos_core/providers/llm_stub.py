"""Stub LLM provider for unit tests - no network calls."""
from __future__ import annotations
from peripatos_core.providers.llm import AgentMessage, LLMProvider, ToolSpec


class StubLLMProvider(LLMProvider):
    """Returns pre-configured responses for testing."""

    def __init__(
        self,
        response: str = "stub response",
        tool_response: AgentMessage | None = None,
    ) -> None:
        self._response = response
        self._tool_response = tool_response or AgentMessage(
            role="assistant",
            content=response,
            tool_calls=None,
        )
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self._response

    def complete_with_tools(
        self,
        messages: list[AgentMessage],
        tools: list[ToolSpec],
    ) -> AgentMessage:
        return self._tool_response
