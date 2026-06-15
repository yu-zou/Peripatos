"""Timing utilities — decorator and context manager for step measurement."""
from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def timed(label: str) -> Callable[[F], F]:
    """Decorator: log elapsed time when the wrapped function completes.

    Works with both standalone functions and methods. Logs even if the
    function raises (re-raises after logging).

    Usage::

        @timed("PDF parsing")
        def parse(self, pdf_path: Path) -> ParsedPaper:
            ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            module_logger = logging.getLogger(func.__module__)
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                module_logger.info("%s completed in %.1fs", label, elapsed)
                return result
            except Exception:
                elapsed = time.perf_counter() - start
                module_logger.info("%s failed after %.1fs", label, elapsed)
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


class _TimedBlock:
    """Context manager that logs elapsed time for a code block.

    Usage::

        with timed_block("Total pipeline"):
            ...
    """

    def __init__(self, label: str, logger: logging.Logger) -> None:
        self._label = label
        self._logger = logger
        self._start: float = 0.0

    def __enter__(self) -> None:
        self._start = time.perf_counter()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        elapsed = time.perf_counter() - self._start
        if exc_type is None:
            self._logger.info("%s completed in %.1fs", self._label, elapsed)
        else:
            self._logger.info("%s failed after %.1fs", self._label, elapsed)
        return False  # do not suppress exceptions


def timed_block(label: str, logger: logging.Logger | None = None) -> _TimedBlock:
    """Create a timed context manager.

    Args:
        label: Human-readable label for the log message.
        logger: Logger to use. Defaults to the peripatos_core root logger.
    """
    if logger is None:
        logger = logging.getLogger("peripatos_core")
    return _TimedBlock(label, logger)
