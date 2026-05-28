"""Tests for CLI commands."""
import sys
from io import StringIO
from contextlib import redirect_stdout
from unittest.mock import patch

from peripatos_core.cli import main


def _run_cli(*args):
    """Run CLI with given args and return (stdout, exit_code)."""
    f = StringIO()
    exit_code = 0
    with redirect_stdout(f), patch.object(sys, "argv", ["peripatos"] + list(args)):
        try:
            main()
        except SystemExit as e:
            exit_code = e.code
    return f.getvalue(), exit_code


def test_help():
    stdout, code = _run_cli("--help")
    assert code == 0
    assert "generate" in stdout
    assert "list-archetypes" in stdout
    assert "doctor" in stdout


def test_list_archetypes():
    stdout, code = _run_cli("list-archetypes")
    assert code == 0
    assert "peer" in stdout
    assert "skeptic" in stdout
    assert "tutor" in stdout
    assert "enthusiast" in stdout


def test_doctor_no_config(tmp_path, monkeypatch):
    """doctor runs without error even with no config file."""
    monkeypatch.setattr("peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json")
    stdout, code = _run_cli("doctor")
    assert code == 0
    assert "LLM provider" in stdout
    assert "TTS provider" in stdout


def test_doctor_with_config(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr("peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json")
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"llm": {"api_key": "test-key", "model": "gpt-4o"}}))
    stdout, code = _run_cli("doctor", "--config", str(cfg))
    assert code == 0
    assert "present" in stdout
    assert "gpt-4o" in stdout


def test_generate_help():
    stdout, code = _run_cli("generate", "--help")
    assert code == 0
    assert "source" in stdout.lower()


def test_doctor_shows_two_voices(tmp_path, monkeypatch):
    """doctor command prints both host and interviewee voices."""
    monkeypatch.setattr("peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json")
    stdout, code = _run_cli("doctor")
    assert code == 0
    assert "TTS host voice" in stdout
    assert "TTS interviewee voice" in stdout


def test_doctor_shows_voice_source(tmp_path, monkeypatch):
    """doctor command shows voice source label."""
    monkeypatch.setattr("peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json")
    stdout, code = _run_cli("doctor")
    assert code == 0
    assert "from default" in stdout or "from config" in stdout or "from legacy" in stdout


def test_doctor_shows_config_voices(tmp_path, monkeypatch):
    """doctor command shows voices from config when tts.voices is set."""
    import json

    monkeypatch.setattr("peripatos_core.config.USER_GLOBAL_CONFIG_PATH", tmp_path / "nonexistent.json")
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({
        "tts": {"voices": {"host": "en-US-GuyNeural", "interviewee": "en-US-JennyNeural"}}
    }))
    stdout, code = _run_cli("doctor", "--config", str(cfg))
    assert code == 0
    assert "en-US-GuyNeural" in stdout
    assert "en-US-JennyNeural" in stdout
    assert "from config" in stdout
