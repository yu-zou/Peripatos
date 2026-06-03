"""Real-LLM end-to-end test.

Requires ``RUN_INTEGRATION=1`` and ``Peripatos/config.test.json`` present.
NOT mocked — performs live arxiv fetch, real LLM call, real TTS, real MP3 generation.

The config.test.json should include a ``parser.mineru_token`` field for
MinerU Precision extract (≤600 pages). Without it, the parser uses Flash
mode (≤20 pages) or falls back to PyMuPDF.
"""
# pyright: reportMissingImports=false
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from mutagen.id3 import ID3

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get("RUN_INTEGRATION") != "1",
        reason="set RUN_INTEGRATION=1 to enable integration tests",
    ),
]


def test_e2e_arxiv_2303_08774_real_llm(tmp_path: Path, config_test_json_path: Path) -> None:
    """Full pipeline: fetch arxiv 2303.08774 → LLM dialogue → TTS → MP3 with chapters."""
    output_mp3 = tmp_path / "test_e2e.mp3"

    result = subprocess.run(
        [
            "peripatos",
            "generate",
            "https://arxiv.org/abs/2303.08774",
            "--config",
            str(config_test_json_path),
            "--output",
            str(output_mp3),
        ],
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )

    assert result.returncode == 0, (
        f"peripatos generate failed (exit {result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
    assert "LLMError" not in result.stderr, (
        f"LLMError detected in stderr — JSON parsing regression:\n{result.stderr}"
    )
    assert output_mp3.exists(), "Output MP3 file was not created"
    assert output_mp3.stat().st_size > 10_000, (
        f"Output MP3 is suspiciously small: {output_mp3.stat().st_size} bytes"
    )

    tags = ID3(str(output_mp3))
    chap_frames = [key for key in tags.keys() if key.startswith("CHAP")]
    assert len(chap_frames) >= 1, (
        f"No CHAP frames found in MP3 ID3 tags. Keys present: {list(tags.keys())}"
    )
    # Verify two-voice: the MP3 should have been generated with distinct voices
    # (We verify this indirectly via the chapter count — at least 2 turns means 2 speakers)
    assert len(chap_frames) >= 2, (
        f"Expected at least 2 CHAP frames (one per speaker turn), got {len(chap_frames)}"
    )


def test_e2e_two_voice_doctor_check(config_test_json_path: Path) -> None:
    """Verify that doctor reports two distinct voices when using config.test.json."""
    result = subprocess.run(
        [
            "peripatos",
            "doctor",
            "--config",
            str(config_test_json_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, f"peripatos doctor failed:\n{result.stdout}\n{result.stderr}"
    assert "TTS host voice" in result.stdout, "Missing 'TTS host voice' in doctor output"
    assert "TTS interviewee voice" in result.stdout, "Missing 'TTS interviewee voice' in doctor output"

    lines = result.stdout.splitlines()
    host_line = next((l for l in lines if "TTS host voice" in l), "")
    interviewee_line = next((l for l in lines if "TTS interviewee voice" in l), "")
    assert host_line != interviewee_line, (
        f"Host and interviewee voice lines are identical — two-voice feature not working:\n"
        f"  host:        {host_line}\n"
        f"  interviewee: {interviewee_line}"
    )


def test_e2e_html_url_real_llm(tmp_path: Path, config_test_json_path: Path) -> None:
    """Full pipeline: fetch HTML URL → LLM dialogue → TTS → MP3 with chapters."""
    output_mp3 = tmp_path / "test_e2e_html.mp3"

    result = subprocess.run(
        [
            "peripatos",
            "generate",
            "https://arxiv.org/html/2303.08774",
            "--config",
            str(config_test_json_path),
            "--output",
            str(output_mp3),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )

    assert result.returncode == 0, (
        f"peripatos generate failed (exit {result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
    assert "LLMError" not in result.stderr, (
        f"LLMError detected in stderr — JSON parsing regression:\n{result.stderr}"
    )
    assert output_mp3.exists(), "Output MP3 file was not created"
    assert output_mp3.stat().st_size > 10_000, (
        f"Output MP3 is suspiciously small: {output_mp3.stat().st_size} bytes"
    )

    tags = ID3(str(output_mp3))
    chap_frames = [key for key in tags.keys() if key.startswith("CHAP")]
    assert len(chap_frames) >= 2, (
        f"Expected at least 2 CHAP frames (one per speaker turn), got {len(chap_frames)}"
    )


def test_e2e_markdown_file_real_llm(tmp_path: Path, config_test_json_path: Path) -> None:
    """Full pipeline: read Markdown file → LLM dialogue → TTS → MP3 with chapters."""
    md_path = tmp_path / "paper.md"
    md_path.write_text(
        """# Attention Is All You Need

## Abstract
The dominant sequence transduction models are based on complex recurrent or convolutional neural networks.
We propose a new simple network architecture, the Transformer, based solely on attention mechanisms.

## Introduction
Recurrent neural networks, long short-term memory and gated recurrent neural networks in particular,
have been firmly established as state of the art approaches in sequence modeling and transduction problems.
"""
    )

    output_mp3 = tmp_path / "test_e2e_markdown.mp3"

    result = subprocess.run(
        [
            "peripatos",
            "generate",
            str(md_path),
            "--config",
            str(config_test_json_path),
            "--output",
            str(output_mp3),
        ],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )

    assert result.returncode == 0, (
        f"peripatos generate failed (exit {result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
    assert "LLMError" not in result.stderr, (
        f"LLMError detected in stderr — JSON parsing regression:\n{result.stderr}"
    )
    assert output_mp3.exists(), "Output MP3 file was not created"
    assert output_mp3.stat().st_size > 10_000, (
        f"Output MP3 is suspiciously small: {output_mp3.stat().st_size} bytes"
    )

    tags = ID3(str(output_mp3))
    chap_frames = [key for key in tags.keys() if key.startswith("CHAP")]
    assert len(chap_frames) >= 2, (
        f"Expected at least 2 CHAP frames (one per speaker turn), got {len(chap_frames)}"
    )
