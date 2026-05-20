"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


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
