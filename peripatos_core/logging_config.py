"""Centralized logging setup for peripatos."""

import logging
import sys
from pathlib import Path

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_LOG_DATEFMT = "%H:%M:%S"


def _make_formatter() -> logging.Formatter:
    """Return the shared log formatter used by console and file handlers."""
    return logging.Formatter(fmt=_LOG_FORMAT, datefmt=_LOG_DATEFMT)


def setup_logging() -> None:
    """Configure stdio logging. Always INFO level, output to stderr.

    Call once at CLI entry before any work. All existing module-level
    ``logger = logging.getLogger(__name__)`` calls produce output after this.
    """
    logging.basicConfig(
        level=logging.INFO,
        format=_LOG_FORMAT,
        datefmt=_LOG_DATEFMT,
        stream=sys.stderr,
    )


def attach_run_log_file(output_path: Path) -> logging.FileHandler:
    """Attach a per-run file handler that mirrors console logging.

    The log file is derived from ``output_path`` by replacing its suffix with
    ``.log`` (e.g. ``podcast.mp3`` -> ``podcast.log``), written in the same
    directory, overwriting any previous run's log. Returns the handler so the
    caller can detach/close it if needed.
    """
    log_path = Path(output_path).with_suffix(".log")
    handler = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    handler.setLevel(logging.INFO)
    handler.setFormatter(_make_formatter())
    logging.getLogger().addHandler(handler)
    return handler