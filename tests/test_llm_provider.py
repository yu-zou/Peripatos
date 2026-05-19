import pytest
from peripatos_core.providers.llm import LLMProvider
from peripatos_core.providers.llm_stub import StubLLMProvider


def test_stub_returns_configured_response():
    provider = StubLLMProvider(response="hello world")
    result = provider.complete("sys", "user")
    assert result == "hello world"


def test_stub_records_calls():
    provider = StubLLMProvider()
    provider.complete("system prompt", "user prompt")
    assert len(provider.calls) == 1
    assert provider.calls[0] == ("system prompt", "user prompt")


def test_stub_is_llm_provider():
    provider = StubLLMProvider()
    assert isinstance(provider, LLMProvider)


def test_stub_multiple_calls():
    provider = StubLLMProvider(response="ok")
    for _ in range(3):
        provider.complete("s", "u")
    assert len(provider.calls) == 3
