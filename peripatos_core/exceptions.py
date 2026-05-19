"""Custom exceptions for Peripatos Core."""


class PeriptatosError(Exception):
    """Base exception for all Peripatos errors."""


class ConfigError(PeriptatosError):
    """Raised when configuration is invalid or missing required fields."""


class FetchError(PeriptatosError):
    """Raised when fetching a paper (ArXiv/URL/local) fails."""


class ParseError(PeriptatosError):
    """Raised when PDF parsing or text extraction fails."""


class LLMError(PeriptatosError):
    """Raised when LLM API call fails or returns unexpected output."""


class TTSError(PeriptatosError):
    """Raised when TTS synthesis fails."""


class AudioError(PeriptatosError):
    """Raised when audio assembly or chapter-marking fails."""
