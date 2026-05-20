"""Real-LLM end-to-end test.

Requires ``RUN_INTEGRATION=1`` and ``Peripatos/config.test.json`` present.
NOT mocked — performs live arxiv fetch, real LLM call, real TTS, real MP3 generation.
"""
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
    assert len(chap_frames) >= 1, (
        f"No CHAP frames found in MP3 ID3 tags. Keys present: {list(tags.keys())}"
    )
