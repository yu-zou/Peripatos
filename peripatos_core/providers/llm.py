"""LLM provider abstraction for Peripatos Core."""
from __future__ import annotations
import logging
import json
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

    def complete_with_tools(
        self,
        messages: list[AgentMessage],
        tools: list[ToolSpec],
    ) -> AgentMessage:
        from peripatos_core.exceptions import LLMError

        try:
            openai_messages = []
            for msg in messages:
                openai_msg: dict = {"role": msg.role, "content": msg.content}
                if msg.tool_call_id is not None:
                    openai_msg["tool_call_id"] = msg.tool_call_id
                if msg.tool_calls:
                    openai_msg["tool_calls"] = [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.name,
                                "arguments": json.dumps(tool_call.arguments),
                            },
                        }
                        for tool_call in msg.tool_calls
                    ]
                openai_messages.append(openai_msg)

            openai_tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool_spec.name,
                        "description": tool_spec.description,
                        "parameters": tool_spec.parameters,
                    },
                }
                for tool_spec in tools
            ]

            response = self._client.chat.completions.create(
                model=self._model,
                messages=openai_messages,
                tools=openai_tools,
                tool_choice="auto",
            )
            response_message = response.choices[0].message
            response_tool_calls = []
            for tool_call in response_message.tool_calls or []:
                response_tool_calls.append(
                    ToolCall(
                        id=tool_call.id,
                        name=tool_call.function.name,
                        arguments=json.loads(tool_call.function.arguments),
                    )
                )

            return AgentMessage(
                role="assistant",
                content=response_message.content,
                tool_calls=response_tool_calls or None,
            )
        except Exception as exc:
            if isinstance(exc, LLMError):
                raise
            raise LLMError(f"LLM API call failed: {exc}") from exc
