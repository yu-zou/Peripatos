"""LLM provider abstraction for Peripatos Core."""
from __future__ import annotations
from abc import ABC, abstractmethod
from peripatos_core.config import LLMConfig


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat completion request and return the response text."""


class OpenAICompatibleLLMProvider(LLMProvider):
    """LLM provider using any OpenAI-compatible API (OpenAI, Requesty, OpenRouter, etc.)."""

    def __init__(self, config: LLMConfig) -> None:
        import openai
        self._client = openai.OpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self._model = config.model

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        from peripatos_core.exceptions import LLMError
        try:
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
