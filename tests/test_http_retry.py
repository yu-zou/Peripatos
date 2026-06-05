"""Tests for peripatos_core.http.request_with_retry shared retry helper."""
from __future__ import annotations

import logging
from unittest.mock import patch, call

import pytest
import requests
import responses

from peripatos_core.http import request_with_retry  # ImportError — RED state

URL = "https://example.test/data"


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def _call(
    method: str = "GET",
    url: str = URL,
    **kwargs,
):
    """Wrap request_with_retry so all tests use the same default signature."""
    return request_with_retry(method, url, **kwargs)


# ==========================================================================
# Test 1 – success on the very first attempt
# ==========================================================================
@responses.activate
def test_success_first_try():
    """First request returns 200 — no retry needed."""
    responses.add(responses.GET, URL, json={"ok": True}, status=200)

    resp = _call()

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert len(responses.calls) == 1


# ==========================================================================
# Test 2 – retry on 500, then succeed
# ==========================================================================
@responses.activate
@patch("time.sleep")
def test_retry_on_500_then_success(mock_sleep):
    """One 500 failure followed by a 200 success — exactly one retry."""
    responses.add(responses.GET, URL, status=500)
    responses.add(responses.GET, URL, json={"ok": True}, status=200)

    resp = _call()

    assert resp.status_code == 200
    assert len(responses.calls) == 2
    mock_sleep.assert_called_once()


# ==========================================================================
# Test 3 – 429 with Retry-After header honoured exactly
# ==========================================================================
@responses.activate
@patch("time.sleep")
def test_retry_on_429_honors_retry_after(mock_sleep):
    """429 response includes Retry-After: 3 — sleep for exactly 3 seconds."""
    responses.add(
        responses.GET, URL, status=429, headers={"Retry-After": "3"}
    )
    responses.add(responses.GET, URL, json={"ok": True}, status=200)

    resp = _call()

    assert resp.status_code == 200
    mock_sleep.assert_called_once()
    assert mock_sleep.call_args[0][0] == pytest.approx(3.0)


# ==========================================================================
# Test 4 – 429 without Retry-After falls back to jitter
# ==========================================================================
@responses.activate
@patch("time.sleep")
@patch("random.uniform", return_value=0.5)
def test_retry_on_429_falls_back_to_jitter_when_header_absent(
    mock_uniform, mock_sleep
):
    """429 without Retry-After header uses the full-jitter value."""
    responses.add(responses.GET, URL, status=429)
    responses.add(responses.GET, URL, json={"ok": True}, status=200)

    resp = _call()

    assert resp.status_code == 200
    mock_sleep.assert_called_once()
    assert mock_sleep.call_args[0][0] == pytest.approx(0.5)


# ==========================================================================
# Test 5 – retry on SSLError, then succeed
# ==========================================================================
@responses.activate
@patch("time.sleep")
def test_retry_on_ssl_eof_then_success(mock_sleep):
    """SSLError (UNEXPECTED_EOF_WHILE_READING) triggers retry, then success."""
    responses.add(
        responses.GET,
        URL,
        body=requests.exceptions.SSLError("UNEXPECTED_EOF_WHILE_READING"),
    )
    responses.add(responses.GET, URL, json={"ok": True}, status=200)

    resp = _call()

    assert resp.status_code == 200
    assert len(responses.calls) == 2
    mock_sleep.assert_called_once()


# ==========================================================================
# Test 6 – retry on ConnectionError, then succeed
# ==========================================================================
@responses.activate
@patch("time.sleep")
def test_retry_on_connection_error_then_success(mock_sleep):
    """ConnectionError triggers retry, second attempt succeeds."""
    responses.add(
        responses.GET,
        URL,
        body=requests.exceptions.ConnectionError("Connection refused"),
    )
    responses.add(responses.GET, URL, json={"ok": True}, status=200)

    resp = _call()

    assert resp.status_code == 200
    assert len(responses.calls) == 2
    mock_sleep.assert_called_once()


# ==========================================================================
# Test 7 – retry on Timeout, then succeed
# ==========================================================================
@responses.activate
@patch("time.sleep")
def test_retry_on_timeout_then_success(mock_sleep):
    """Timeout triggers retry, second attempt succeeds."""
    responses.add(
        responses.GET,
        URL,
        body=requests.exceptions.Timeout("Read timed out"),
    )
    responses.add(responses.GET, URL, json={"ok": True}, status=200)

    resp = _call()

    assert resp.status_code == 200
    assert len(responses.calls) == 2
    mock_sleep.assert_called_once()


# ==========================================================================
# Test 8 – 401 is NOT retried
# ==========================================================================
@responses.activate
def test_no_retry_on_401():
    """Client error 401 returns immediately — no retry."""
    responses.add(responses.GET, URL, status=401)

    resp = _call()

    assert resp.status_code == 401
    assert len(responses.calls) == 1


# ==========================================================================
# Test 9 – 404 is NOT retried
# ==========================================================================
@responses.activate
def test_no_retry_on_404():
    """Client error 404 returns immediately — no retry."""
    responses.add(responses.GET, URL, status=404)

    resp = _call()

    assert resp.status_code == 404
    assert len(responses.calls) == 1


# ==========================================================================
# Test 10 – 400 is NOT retried
# ==========================================================================
@responses.activate
def test_no_retry_on_400():
    """Client error 400 returns immediately — no retry."""
    responses.add(responses.GET, URL, status=400)

    resp = _call()

    assert resp.status_code == 400
    assert len(responses.calls) == 1


# ==========================================================================
# Test 11 – exhaust all retries on HTTP errors → HTTPError
# ==========================================================================
@responses.activate
@patch("time.sleep")
def test_exhaust_retries_raises(mock_sleep):
    """After 5 × 503 the helper raises requests.HTTPError."""
    for _ in range(5):
        responses.add(responses.GET, URL, status=503)

    with pytest.raises(requests.HTTPError):
        _call()

    assert len(responses.calls) == 5


# ==========================================================================
# Test 12 – exhaust all retries on exceptions → last exception re-raised
# ==========================================================================
@responses.activate
@patch("time.sleep")
def test_exhaust_retries_on_exception_raises(mock_sleep):
    """After 5 × SSLError the helper re-raises the last SSLError."""
    for _ in range(5):
        responses.add(
            responses.GET,
            URL,
            body=requests.exceptions.SSLError("UNEXPECTED_EOF_WHILE_READING"),
        )

    with pytest.raises(requests.exceptions.SSLError):
        _call()

    assert len(responses.calls) == 5


# ==========================================================================
# Test 13 – full-jitter delay stays within exponential bounds
# ==========================================================================
@responses.activate
@patch("time.sleep")
@patch("random.uniform")
def test_full_jitter_within_bounds(mock_uniform, mock_sleep):
    """Full-jitter calls random.uniform(0, base_delay * 2^attempt)."""
    mock_uniform.return_value = 0.42
    responses.add(responses.GET, URL, status=503)
    responses.add(responses.GET, URL, status=503)
    responses.add(responses.GET, URL, json={"ok": True}, status=200)

    resp = _call()

    assert resp.status_code == 200
    assert mock_uniform.call_count == 2
    # Attempt 0: uniform(0, 1.0 * 2**0) = uniform(0, 1.0)
    assert mock_uniform.call_args_list[0] == call(0, 1.0)
    # Attempt 1: uniform(0, 1.0 * 2**1) = uniform(0, 2.0)
    assert mock_uniform.call_args_list[1] == call(0, 2.0)


# ==========================================================================
# Test 14 – Retry-After value capped at 60 s
# ==========================================================================
@responses.activate
@patch("time.sleep")
def test_max_delay_cap_on_retry_after(mock_sleep):
    """429 with Retry-After: 120 is clamped to the 60-second maximum."""
    responses.add(
        responses.GET, URL, status=429, headers={"Retry-After": "120"}
    )
    responses.add(responses.GET, URL, json={"ok": True}, status=200)

    resp = _call()

    assert resp.status_code == 200
    mock_sleep.assert_called_once()
    assert mock_sleep.call_args[0][0] == pytest.approx(60.0)


# ==========================================================================
# Test 15 – stream=True is passed through transparently
# ==========================================================================
@responses.activate
def test_stream_true_passthrough():
    """stream=True reaches requests; iter_content remains callable."""
    responses.add(
        responses.GET,
        URL,
        body=b"chunk1chunk2",
        status=200,
    )

    resp = _call(stream=True)

    assert resp.status_code == 200
    assert callable(resp.iter_content)
    assert len(responses.calls) == 1


# ==========================================================================
# Test 16 – WARNING is logged on every retry
# ==========================================================================
@responses.activate
@patch("time.sleep")
def test_logger_warns_on_retry(mock_sleep, caplog):
    """A WARNING log record is emitted for each retry attempt."""
    caplog.set_level(logging.WARNING)
    responses.add(responses.GET, URL, status=500)
    responses.add(responses.GET, URL, json={"ok": True}, status=200)

    _call()

    assert len(responses.calls) == 2
    warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) >= 1, "expected at least one WARNING for the retry"
