"""Tests for custom exception hierarchy."""
import pytest

from peripatos_core.exceptions import (
    AudioError,
    ConfigError,
    FetchError,
    LLMError,
    ParseError,
    PeriptatosError,
    TTSError,
)


def test_all_inherit_from_base():
    for exc_cls in [ConfigError, FetchError, ParseError, LLMError, TTSError, AudioError]:
        assert issubclass(exc_cls, PeriptatosError)
        assert issubclass(exc_cls, Exception)


def test_raise_and_catch_config_error():
    with pytest.raises(ConfigError, match="bad config"):
        raise ConfigError("bad config")


def test_raise_and_catch_fetch_error():
    with pytest.raises(FetchError):
        raise FetchError("network failure")


def test_catch_as_base():
    with pytest.raises(PeriptatosError):
        raise LLMError("model error")
