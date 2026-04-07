from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

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

    command = cast(str, args.command)
    source = cast(str, args.source)
    persona = cast(str, args.persona)
    language = cast(str, args.language)
    tts_engine = cast(str, args.tts_engine)
    output_dir_value = cast(str, args.output_dir)
    llm_provider = cast(str, args.llm_provider)
    llm_model = cast(str, args.llm_model)
    verbose = cast(bool, args.verbose)

    assert command == "generate"
    assert source == "2408.09869"
    assert persona == "tutor"
    assert language == "zh-en"
    assert tts_engine == "edge-tts"
    assert output_dir_value == str(output_dir)
    assert llm_provider == "anthropic"
    assert llm_model == "claude-3-opus"
    assert verbose is True


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    parser = create_parser()
    with pytest.raises(SystemExit):
        _ = parser.parse_args(["--version"])
    captured = capsys.readouterr()
    assert __version__ in captured.out


def test_help_flag(capsys: pytest.CaptureFixture[str]) -> None:
    parser = create_parser()
    with pytest.raises(SystemExit):
        _ = parser.parse_args(["--help"])
    captured = capsys.readouterr()
    assert "usage" in captured.out.lower()
    assert "peripatos generate" in captured.out


def test_invalid_source_error(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "argv", ["peripatos", "generate", "not-a-source"])
    with pytest.raises(SystemExit):
        _ = main()
    captured = capsys.readouterr()
    assert "Invalid source" in captured.err


def test_detect_source_type(tmp_path: Path) -> None:
    pdf_path = tmp_path / "paper.pdf"
    _ = pdf_path.write_bytes(b"%PDF-1.4 test")

    arxiv_type = detect_source_type("2408.09869")
    pdf_type = detect_source_type(str(pdf_path))

    assert arxiv_type == "arxiv"
    assert pdf_type == "pdf"


def test_vlm_flag_parsed_correctly() -> None:
    """Test that --vlm flag is parsed and stored in args.vlm"""
    parser = create_parser()
    args = parser.parse_args(["generate", "2408.09869", "--vlm"])
    
    vlm = cast(bool, args.vlm)
    assert vlm is True


def test_vlm_flag_defaults_to_false() -> None:
    """Test that vlm flag defaults to False when not provided"""
    parser = create_parser()
    args = parser.parse_args(["generate", "2408.09869"])
    
    vlm = cast(bool, getattr(args, "vlm", False))
    assert vlm is False


def test_vlm_flag_is_store_true_action() -> None:
    """Test that --vlm uses store_true action (no argument needed)"""
    parser = create_parser()
    # Should not raise an error when parsing --vlm without a value
    args = parser.parse_args(["generate", "2408.09869", "--vlm"])
    
    vlm = cast(bool, args.vlm)
    assert vlm is True


def test_vlm_flag_in_help_text(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that --vlm flag appears in help text"""
    parser = create_parser()
    with pytest.raises(SystemExit):
        _ = parser.parse_args(["generate", "--help"])
    captured = capsys.readouterr()
    
    assert "--vlm" in captured.out
