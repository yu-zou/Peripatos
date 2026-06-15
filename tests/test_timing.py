"""Tests for the timing module."""
import logging
import time

from peripatos_core.timing import timed, timed_block


def test_timed_decorator_logs_success(caplog):
    """@timed logs completion time on normal return."""
    caplog.set_level(logging.INFO)

    @timed("test operation")
    def do_work():
        return 42

    result = do_work()
    assert result == 42
    assert "test operation completed in" in caplog.text


def test_timed_decorator_logs_failure(caplog):
    """@timed logs failure time and re-raises."""
    caplog.set_level(logging.INFO)

    @timed("failing operation")
    def do_fail():
        raise ValueError("boom")

    try:
        do_fail()
    except ValueError:
        pass

    assert "failing operation failed after" in caplog.text


def test_timed_decorator_preserves_name():
    """@timed does not break function metadata."""
    @timed("something")
    def my_func():
        pass

    assert my_func.__name__ == "my_func"


def test_timed_decorator_on_method(caplog):
    """@timed works on class methods with self."""
    caplog.set_level(logging.INFO)

    class Worker:
        @timed("method work")
        def do_stuff(self, x):
            return x * 2

    w = Worker()
    result = w.do_stuff(5)
    assert result == 10
    assert "method work completed in" in caplog.text


def test_timed_block_logs_success(caplog):
    """timed_block logs on normal exit."""
    caplog.set_level(logging.INFO)

    with timed_block("the block"):
        pass

    assert "the block completed in" in caplog.text


def test_timed_block_logs_failure(caplog):
    """timed_block logs and re-raises on exception."""
    caplog.set_level(logging.INFO)

    try:
        with timed_block("failing block"):
            raise RuntimeError("oops")
    except RuntimeError:
        pass

    assert "failing block failed after" in caplog.text
