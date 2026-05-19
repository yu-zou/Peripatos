"""Stub LLM provider for unit tests - no network calls."""
from __future__ import annotations
from peripatos_core.providers.llm import LLMProvider


class StubLLMProvider(LLMProvider):
    """Returns pre-configured responses for testing."""

    def __init__(self, response: str = "stub response") -> None:
        self._response = response
        self.calls: list[tuple[str, str]] = []

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        self.calls.append((system_prompt, user_prompt))
        return self._response
