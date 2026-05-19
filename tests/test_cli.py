"""Tests for CLI commands."""
import pytest
from typer.testing import CliRunner
from peripatos_core.cli import app

runner = CliRunner()


def test_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "generate" in result.output
    assert "list-archetypes" in result.output
    assert "doctor" in result.output


def test_list_archetypes():
    result = runner.invoke(app, ["list-archetypes"])
    assert result.exit_code == 0
    assert "proxy_host" in result.output
    assert "author_persona" in result.output
    assert "devils_advocate" in result.output
    assert "domain_expert" in result.output


def test_doctor_no_config(tmp_path, monkeypatch):
    """doctor runs without error even with no config file."""
    monkeypatch.setattr("peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json")
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "LLM provider" in result.output
    assert "TTS provider" in result.output


def test_doctor_with_config(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr("peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json")
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"llm": {"api_key": "test-key", "model": "gpt-4o"}}))
    result = runner.invoke(app, ["doctor", "--config", str(cfg)])
    assert result.exit_code == 0
    assert "present" in result.output
    assert "gpt-4o" in result.output


def test_generate_help():
    result = runner.invoke(app, ["generate", "--help"])
    assert result.exit_code == 0
    assert "source" in result.output.lower() or "SOURCE" in result.output
