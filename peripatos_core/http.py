from __future__ import annotations

import logging
import random
import time
from typing import Any, Mapping

import requests

__all__ = ["request_with_retry"]

_RETRYABLE_HTTP_CODES: frozenset[int] = frozenset({429, 500, 502, 503, 504})
_RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    requests.exceptions.SSLError,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)
_MAX_RETRY_AFTER_SECONDS: float = 60.0

_LOGGER = logging.getLogger(__name__)


def request_with_retry(
    method: str,
    url: str,
    *,
    json: Any | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = 60.0,
    stream: bool = False,
    max_retries: int = 5,
    base_delay: float = 1.0,
) -> requests.Response:
    """Make an HTTP request with automatic retry on transient failures.

    Retries on: SSLError, ConnectionError, Timeout, HTTP 429/500/502/503/504.
    Non-retryable responses (e.g. 400, 401, 403, 404) are returned immediately.

    Full-jitter exponential backoff: random.uniform(0, base_delay * 2**attempt).
    On 429, Retry-After header is honoured (clamped to 60 s).

    Caller is responsible for ensuring requests are safe to retry. POST/PUT
    calls are retried; ensure they are idempotent before using this helper.

    Returns the final requests.Response. Raises the last exception when all
    retries fail on a network error, or requests.HTTPError when all retries
    fail on a retryable HTTP status.
    """
    last_exc: Exception | None = None
    last_resp: requests.Response | None = None

    for attempt in range(max_retries):
        try:
            resp = requests.request(
                method, url,
                json=json, headers=headers,
                timeout=timeout, stream=stream,
            )
        except _RETRYABLE_EXCEPTIONS as exc:
            delay = random.uniform(0, base_delay * (2 ** attempt))
            _LOGGER.warning(
                "retry attempt=%d/%d reason=%s delay=%.2fs",
                attempt + 1, max_retries, type(exc).__name__, delay,
            )
            time.sleep(delay)
            last_exc = exc
            continue

        if resp.status_code in _RETRYABLE_HTTP_CODES:
            # Honor Retry-After on 429, fall back to jitter otherwise
            delay = _get_delay(resp, attempt, base_delay)
            _LOGGER.warning(
                "retry attempt=%d/%d status=%d delay=%.2fs",
                attempt + 1, max_retries, resp.status_code, delay,
            )
            time.sleep(delay)
            last_resp = resp
            continue

        # Non-retryable (2xx, 4xx other than 429, 3xx) — return immediately
        return resp

    # All attempts exhausted
    if last_exc is not None:
        raise last_exc
    raise requests.HTTPError(response=last_resp)


def _get_delay(resp: requests.Response, attempt: int, base_delay: float) -> float:
    """Return sleep duration: Retry-After (clamped) or full-jitter backoff."""
    retry_after = resp.headers.get("Retry-After")
    if retry_after is not None:
        try:
            return max(0.0, min(float(retry_after), _MAX_RETRY_AFTER_SECONDS))
        except ValueError:
            pass
    return random.uniform(0, base_delay * (2 ** attempt))
