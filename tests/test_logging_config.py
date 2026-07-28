"""Tests for logging configuration."""
import logging
import sys
from pathlib import Path

from peripatos_core.logging_config import setup_logging, attach_run_log_file


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


def test_attach_run_log_file_derives_log_suffix(tmp_path):
    output = tmp_path / "podcast.mp3"
    handler = attach_run_log_file(output)
    try:
        expected = tmp_path / "podcast.log"
        assert Path(handler.baseFilename) == expected
        assert expected.exists()
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()


def test_attach_run_log_file_writes_records(tmp_path):
    output = tmp_path / "out.mp3"
    handler = attach_run_log_file(output)
    logger = logging.getLogger("peripatos_core.test")
    try:
        logger.warning("hello-log-line")
        handler.flush()
        contents = (tmp_path / "out.log").read_text(encoding="utf-8")
        assert "hello-log-line" in contents
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()


def test_attach_run_log_file_overwrites(tmp_path):
    output = tmp_path / "out.mp3"
    log_path = tmp_path / "out.log"
    log_path.write_text("stale-previous-run\n", encoding="utf-8")
    handler = attach_run_log_file(output)
    try:
        handler.flush()
        contents = log_path.read_text(encoding="utf-8")
        assert "stale-previous-run" not in contents
    finally:
        logging.getLogger().removeHandler(handler)
        handler.close()
