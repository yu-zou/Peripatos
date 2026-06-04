"""Tests for CLI commands."""
import sys
from io import StringIO
from contextlib import redirect_stdout
from unittest.mock import patch

from peripatos_core.cli import main


def test_save_script_json_writes_file(tmp_path):
    """_save_script_json writes valid JSON next to output path."""
    from peripatos_core.cli import _save_script_json
    from peripatos_core.types import DialogueScript, DialogueTurn, Chapter, ArchetypeId
    import json

    script = DialogueScript(
        title="Test Paper",
        chapters=[
            Chapter(
                title="Intro",
                turns=[
                    DialogueTurn(speaker="Host", text="Hello", archetype=ArchetypeId.PEER),
                    DialogueTurn(speaker="Guest", text="Hi", archetype=ArchetypeId.PEER),
                ],
            )
        ],
        intro_turns=[],
        outro_turns=[],
    )
    output_path = tmp_path / "podcast.mp3"
    _save_script_json(script, output_path)

    json_path = tmp_path / "podcast.json"
    assert json_path.exists()
    data = json.loads(json_path.read_text())
    assert data["title"] == "Test Paper"
    assert len(data["chapters"]) == 1
    assert len(data["chapters"][0]["turns"]) == 2


def test_save_script_json_warns_on_failure(tmp_path, caplog):
    """_save_script_json logs a warning on write failure but does not raise."""
    from peripatos_core.cli import _save_script_json
    from peripatos_core.types import DialogueScript, DialogueTurn, Chapter, ArchetypeId

    script = DialogueScript(
        title="Test",
        chapters=[Chapter(title="C", turns=[DialogueTurn(speaker="H", text="T", archetype=ArchetypeId.PEER)])],
        intro_turns=[],
        outro_turns=[],
    )
    # Point output to a read-only directory
    read_only = tmp_path / "readonly"
    read_only.mkdir()
    read_only.chmod(0o000)
    output_path = read_only / "podcast.mp3"

    import logging
    with caplog.at_level(logging.WARNING):
        _save_script_json(script, output_path)

    assert "Could not save script JSON" in caplog.text
    # Clean up for pytest
    read_only.chmod(0o755)


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


def test_save_script_json_changes_mp3_suffix_to_json(tmp_path):
    from peripatos_core.cli import _save_script_json
    from peripatos_core.types import DialogueScript, DialogueTurn, Chapter, ArchetypeId

    script = DialogueScript(
        title="Test Paper",
        chapters=[
            Chapter(
                title="Intro",
                turns=[DialogueTurn(speaker="Host", text="Hello", archetype=ArchetypeId.PEER)],
            )
        ],
        intro_turns=[],
        outro_turns=[],
    )
    output_path = tmp_path / "podcast.mp3"
    _save_script_json(script, output_path)

    json_path = tmp_path / "podcast.json"
    assert json_path.exists()
    assert not tmp_path.joinpath("podcast.mp3.json").exists()


def test_save_script_json_preserves_structure_with_intro_outro(tmp_path):
    from peripatos_core.cli import _save_script_json
    from peripatos_core.types import DialogueScript, DialogueTurn, Chapter, ArchetypeId
    import json

    script = DialogueScript(
        title="Test Paper",
        chapters=[
            Chapter(
                title="Intro",
                turns=[DialogueTurn(speaker="Host", text="Hello", archetype=ArchetypeId.PEER)],
            )
        ],
        intro_turns=[
            DialogueTurn(speaker="Host", text="Welcome!", archetype=ArchetypeId.PEER),
            DialogueTurn(speaker="Guest", text="Thanks!", archetype=ArchetypeId.TUTOR),
        ],
        outro_turns=[
            DialogueTurn(speaker="Host", text="Goodbye!", archetype=ArchetypeId.PEER),
        ],
    )
    output_path = tmp_path / "podcast.mp3"
    _save_script_json(script, output_path)

    json_path = tmp_path / "podcast.json"
    data = json.loads(json_path.read_text())
    assert len(data["intro_turns"]) == 2
    assert data["intro_turns"][0]["speaker"] == "Host"
    assert data["intro_turns"][0]["text"] == "Welcome!"
    assert data["intro_turns"][1]["speaker"] == "Guest"
    assert data["intro_turns"][1]["text"] == "Thanks!"
    assert len(data["outro_turns"]) == 1
    assert data["outro_turns"][0]["speaker"] == "Host"
    assert data["outro_turns"][0]["text"] == "Goodbye!"


def test_save_script_json_handles_nested_dataclass(tmp_path):
    from peripatos_core.cli import _save_script_json
    from peripatos_core.types import DialogueScript, DialogueTurn, Chapter, ArchetypeId
    import json

    script = DialogueScript(
        title="Test Paper",
        chapters=[
            Chapter(
                title="Discussion",
                turns=[
                    DialogueTurn(speaker="Host", text="Q1", archetype=ArchetypeId.PEER),
                    DialogueTurn(speaker="Guest", text="A1", archetype=ArchetypeId.SKEPTIC),
                ],
            ),
            Chapter(
                title="Summary",
                turns=[
                    DialogueTurn(speaker="Host", text="Wrap up", archetype=ArchetypeId.TUTOR),
                ],
            ),
        ],
        intro_turns=[],
        outro_turns=[],
    )
    output_path = tmp_path / "podcast.mp3"
    _save_script_json(script, output_path)

    json_path = tmp_path / "podcast.json"
    data = json.loads(json_path.read_text())
    assert len(data["chapters"]) == 2
    assert data["chapters"][0]["title"] == "Discussion"
    assert data["chapters"][0]["turns"][0]["archetype"] == "peer"
    assert data["chapters"][0]["turns"][1]["archetype"] == "skeptic"
    assert data["chapters"][1]["turns"][0]["archetype"] == "tutor"
