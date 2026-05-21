"""LLM provider abstraction for Peripatos Core."""
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from peripatos_core.config import LLMConfig


logger = logging.getLogger(__name__)


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ToolCallResult:
    tool_call_id: str
    content: str


@dataclass
class AgentMessage:
    role: str
    content: str | None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat completion request and return the response text."""

    @abstractmethod
    def complete_with_tools(
        self,
        messages: list[AgentMessage],
        tools: list[ToolSpec],
    ) -> AgentMessage:
        """Send a chat completion with tool definitions and return the next message."""


class OpenAICompatibleLLMProvider(LLMProvider):
    """LLM provider using any OpenAI-compatible API (OpenAI, Requesty, OpenRouter, etc.)."""

    def __init__(self, config: LLMConfig) -> None:
        import openai  # type: ignore[reportMissingImports]
        self._client = openai.OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self._model = config.model

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        import openai  # type: ignore[reportMissingImports]
        from peripatos_core.exceptions import LLMError
        try:
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                )
            except openai.BadRequestError as exc:
                logger.warning(
                    "LLM provider rejected response_format=json_object; retrying without it: %s",
                    exc,
                )
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                )
            content = response.choices[0].message.content
            if content is None:
                raise LLMError("LLM returned empty response")
            return content
        except Exception as exc:
            if isinstance(exc, LLMError):
                raise
            raise LLMError(f"LLM API call failed: {exc}") from exc
