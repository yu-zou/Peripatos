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


class RAGError(PeriptatosError):
    """Base exception for RAG pipeline errors."""


class EmbeddingError(RAGError):
    """Raised when an embedding API call fails."""


class RetrievalError(RAGError):
    """Raised when vector store retrieval fails."""


class IngestError(RAGError):
    """Raised when source ingestion fails."""


class AgentError(RAGError):
    """Raised when the ReAct agent loop fails (e.g., zero turns produced)."""
