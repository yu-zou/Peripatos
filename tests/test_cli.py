from __future__ import annotations

import sys
from pathlib import Path

import pytest

from peripatos import __version__
from peripatos.cli import create_parser, detect_source_type, main


def test_argparse_all_arguments(tmp_path: Path) -> None:
    parser = create_parser()
    output_dir = tmp_path / "out"
    args = parser.parse_args(
        [
            "generate",
            "2408.09869",
            "--persona",
            "tutor",
            "--language",
            "zh-en",
            "--tts-engine",
            "edge-tts",
            "--output-dir",
            str(output_dir),
            "--llm-provider",
            "anthropic",
            "--llm-model",
            "claude-3-opus",
            "--verbose",
        ]
    )

    assert args.command == "generate"
    assert args.source == "2408.09869"
    assert args.persona == "tutor"
    assert args.language == "zh-en"
    assert args.tts_engine == "edge-tts"
    assert args.output_dir == str(output_dir)
    assert args.llm_provider == "anthropic"
    assert args.llm_model == "claude-3-opus"
    assert args.verbose is True


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    parser = create_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--version"])
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_help_flag(capsys: pytest.CaptureFixture[str]) -> None:
    parser = create_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--help"])
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()
    assert "peripatos generate" in captured.out


def test_invalid_source_error(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["peripatos", "generate", "not-a-source"])
    with pytest.raises(SystemExit):
        main()
    captured = capsys.readouterr()
    assert "Invalid source" in captured.err


def test_detect_source_type(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")

    assert detect_source_type("2408.09869") == "arxiv"
    assert detect_source_type(str(pdf_path)) == "pdf"
