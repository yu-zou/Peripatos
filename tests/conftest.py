"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

import pytest

# Suppress PyMuPDF/swig C extension DeprecationWarnings emitted at
# module registration time. These come from the swigvarlink, SwigPyObject,
# and SwigPyPacked C types which lack __module__ attributes. This is an
# upstream issue in PyMuPDF's SWIG bindings and cannot be fixed from our side.
# Note: some of these fire during C extension init before pytest filters apply,
# so we also set filters in pyproject.toml [tool.pytest.ini_options].filterwarnings.
warnings.filterwarnings("ignore", message=".*has no __module__.*", category=DeprecationWarning)


collect_ignore_glob = (
    [] if os.environ.get("RUN_INTEGRATION") == "1" else ["test_e2e.py"]
)


@pytest.fixture(scope="session")
def config_test_json_path() -> Path:
    """Return path to config.test.json; skip if not present."""
    path = Path(__file__).resolve().parents[1] / "config.test.json"
    if not path.exists():
        pytest.skip("config.test.json not present — integration test skipped")
    return path


@pytest.fixture(scope="session")
def config_test_json(config_test_json_path: Path) -> dict:
    """Return parsed config.test.json as a dict."""
    return json.loads(config_test_json_path.read_text())
