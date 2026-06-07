"""Pytest configuration and shared fixtures."""

from __future__ import annotations

# ── Pre-import pymupdf with SWIG warnings suppressed ──────────────────────
# pymupdf's SWIG C extension emits DeprecationWarnings during type registration
# ("builtin type swigvarlink/SwigPyObject/SwigPyPacked has no __module__").
# By importing here inside catch_warnings(), we register the types silently.
# Python caches module imports, so all later imports of pymupdf are no-ops.
# This must happen BEFORE pytest wraps the session in its own catch_warnings
# contexts (collection/execution), which reset module-level warning filters.
#
# The same warning also fires during interpreter shutdown when the C types are
# finalized. That emission bypasses Python's warnings module entirely — it
# writes directly to file descriptor 2 via the C runtime. We use an atexit
# handler that replaces sys.stderr with /dev/null at shutdown; by that point
# all test output is complete, so no legitimate errors are suppressed.
#
# See SWIG upstream: https://github.com/swig/swig/issues/2881
# See pytest upstream: https://github.com/pytest-dev/pytest/issues/13485
import atexit
import os
import sys
import warnings

with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message=r"builtin type \w+ has no __module__",
        category=DeprecationWarning,
    )
    try:
        import pymupdf  # noqa: F401  # type: ignore[reportMissingImports]
    except ImportError:
        pass  # pymupdf not installed; tests that need it will fail explicitly


def _suppress_swig_shutdown_warnings() -> None:
    """Redirect stderr to /dev/null to suppress C-level SWIG type warnings.

    At interpreter shutdown, pymupdf's SWIG C types emit DeprecationWarnings
    directly via the C runtime (fprintf to stderr), bypassing Python's
    warnings module. All test output is complete by the time atexit runs, so
    this redirect is safe.
    """
    sys.stderr.flush()
    devnull = open(os.devnull, "w")  # noqa: SIM115
    sys.stderr = devnull


atexit.register(_suppress_swig_shutdown_warnings)

# ── Normal imports ──────────────────────────────────────────────────────────
import json
from pathlib import Path

import pytest

# Backup: keep the module-level filter for any SWIG warnings that might still
# leak (e.g., from faiss-cpu if it also uses SWIG internally).
warnings.filterwarnings(
    "ignore",
    message=r".*has no __module__.*",
    category=DeprecationWarning,
)


@pytest.fixture(scope="session")
def config_test_json_path() -> Path:
    """Return path to config.test.json; fail if not present."""
    path = Path(__file__).resolve().parents[1] / "config.test.json"
    if not path.exists():
        pytest.fail(
            "config.test.json not found — create it with your LLM API key and TTS config.\n"
            "See config.example.json for the format. Required for E2E integration tests."
        )
    return path


@pytest.fixture(scope="session")
def config_test_json(config_test_json_path: Path) -> dict:
    """Return parsed config.test.json as a dict."""
    return json.loads(config_test_json_path.read_text())