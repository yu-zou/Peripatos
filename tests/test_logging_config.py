"""Tests for logging configuration."""
import logging
import sys

from peripatos_core.logging_config import setup_logging


def test_setup_logging_configures_root_handler():
    """setup_logging() adds a StreamHandler to stderr at INFO level."""
    # Reset logging to a blank slate
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.NOTSET)

    setup_logging()

    # Root logger should have at least one handler
    assert len(root.handlers) >= 1
    handler = root.handlers[0]
    assert root.level == logging.INFO
    assert isinstance(handler, logging.StreamHandler)
    assert handler.stream is sys.stderr
