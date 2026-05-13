"""End-to-end tests for chapter consolidation, signposts, mixing, and ID3v2 markers."""
from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Any
from unittest.mock import Mock, patch

from peripatos.brain.chapters import consolidate_chapters
from peripatos.cli import _build_chapters, _consolidate_and_insert_signposts, main
from peripatos.config import PeripatosConfig
from peripatos.models import (
    AudioSegment,
    DialogueScript,
    DialogueTurn,
    LanguageMode,
    PaperMetadata,
    PersonaType,
    SectionInfo,
    SectionType,
    SpeakerRole,
)
from peripatos.voice.mixer import AudioMixer


def _make_wave_bytes(duration_ms: int = 100) -> bytes:
    """Create valid in-memory audio bytes for tests without external TTS calls."""
    import io

    frame_rate = 8000
    frames = int(frame_rate * duration_ms / 1000)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(frame_rate)
        wav.writeframes(b"\x00\x00" * frames)
    return buf.getvalue()


def _export_silence_mp3(path: Path, duration_ms: int) -> None:
    """Use ffmpeg to create pydub-equivalent silent MP3 test audio."""
    audio = _make_wave_bytes(duration_ms)
    import subprocess

    _ = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "wav",
            "-i",
            "pipe:0",
            "-f",
            "mp3",
            "-y",
            str(path),
        ],
        input=audio,
        check=True,
        capture_output=True,
    )


def _make_mock_audio_bytes(duration_ms: int = 100) -> bytes:
    """Return valid MP3 bytes representing silence for mocked TTS responses."""
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".mp3") as tmp:
        _export_silence_mp3(Path(tmp.name), duration_ms)
        return Path(tmp.name).read_bytes()


class _FakePydubSegment:
    """Small pydub stand-in that preserves durations and exports valid MP3 silence."""

    def __init__(self, duration_ms: int) -> None:
        self.duration_ms = duration_ms

    def __len__(self) -> int:
        return self.duration_ms

    def __add__(self, other: "_FakePydubSegment") -> "_FakePydubSegment":
        return _FakePydubSegment(self.duration_ms + other.duration_ms)

    def export(self, path: Path, format: str) -> None:
        assert format == "mp3"
        _export_silence_mp3(Path(path), self.duration_ms)

    @classmethod
    def from_mp3(cls, _source: object) -> "_FakePydubSegment":
        return cls(100)

    @classmethod
    def silent(cls, duration: int) -> "_FakePydubSegment":
        return cls(duration)


def _make_paper(section_titles: list[str], source_path: Path) -> PaperMetadata:
    return PaperMetadata(
        title="Chapter Integration Paper",
        authors=["Test Author"],
        abstract="A test paper for complete chapter marker verification.",
        source_path=source_path,
        sections=[
            SectionInfo(
                title=title,
                content=f"Detailed content for {title}.",
                section_type=SectionType.OTHER,
            )
            for title in section_titles
        ],
    )


def _make_config(output_dir: Path) -> PeripatosConfig:
    return PeripatosConfig(
        llm_provider="openai",
        llm_model="gpt-4o",
        tts_engine="openai",
        tts_voice_host="alloy",
        tts_voice_expert="onyx",
        persona="tutor",
        language="en",
        output_dir=str(output_dir),
        openai_api_key="test-key",
        anthropic_api_key=None,
    )


def _section_response(section_title: str, turns_per_section: int = 2) -> str:
    payload: list[dict[str, str]] = []
    for idx in range(turns_per_section):
        speaker = "HOST" if idx % 2 == 0 else "EXPERT"
        payload.append(
            {
                "speaker": speaker,
                "text": f"{speaker.title()} discusses {section_title} turn {idx + 1}.",
            }
        )
    return json.dumps(payload)


def _run_cli_with_mocked_io(
    tmp_path: Path,
    monkeypatch: Any,
    section_titles: list[str],
    turns_per_section: int,
    tts_duration_ms: int = 100,
) -> Path:
    source_pdf = tmp_path / "source.pdf"
    _ = source_pdf.write_bytes(b"%PDF-1.4 mocked pdf")
    output_dir = tmp_path / "out"
    config = _make_config(output_dir)
    paper = _make_paper(section_titles, source_pdf)
    mock_audio_bytes = _make_mock_audio_bytes(tts_duration_ms)

    mock_openai_module = Mock()
    mock_llm_client = Mock()
    mock_openai_module.OpenAI.return_value = mock_llm_client
    mock_llm_client.chat.completions.create.side_effect = [
        Mock(choices=[Mock(message=Mock(content=_section_response(title, turns_per_section)))])
        for title in section_titles
    ]

    def import_side_effect(name: str):
        if name == "openai":
            return mock_openai_module
        return __import__(name, fromlist=[name.split(".")[-1]])

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def render_side_effect(script: DialogueScript, progress_callback: object = None):
        segments = []
        for idx, turn in enumerate(script.turns):
            if callable(progress_callback):
                progress_callback(idx + 1, len(script.turns))
            segments.append(
                AudioSegment(
                    speaker=turn.speaker,
                    audio_bytes=mock_audio_bytes,
                    duration_seconds=tts_duration_ms / 1000,
                    text=turn.text,
                )
            )
        return segments

    fake_render = Mock(side_effect=lambda script, _config, _verbose: render_side_effect(script))
    with patch.dict(
        main.__globals__,
        {
            "load_config": Mock(return_value=config),
            "_parse_pdf": Mock(return_value=paper),
            "_render_audio": fake_render,
        },
    ), patch.dict(
        AudioMixer._concatenate_segments.__globals__,
        {"PydubAudioSegment": _FakePydubSegment},
    ), patch("peripatos.brain.generator.importlib.import_module") as mock_import:
        mock_import.side_effect = import_side_effect

        result = main(["generate", str(source_pdf), "--output-dir", str(output_dir)])

    assert result == 0
    assert mock_llm_client.chat.completions.create.call_count == len(section_titles)
    assert fake_render.call_count == 1
    expected = output_dir / "source_tutor_en.mp3"
    assert expected.exists()
    return expected


def _read_id3_chapter_frames(output_path: Path):
    from mutagen.id3 import ID3  # pyright: ignore[reportMissingImports]

    tags = ID3(str(output_path))
    return [frame for frame in tags.getall("CHAP") if frame.element_id.startswith("chp")], tags.getall("CTOC")


def test_full_pipeline_writes_readable_chap_and_ctoc_frames(tmp_path, monkeypatch):
    """Full CLI path produces ID3v2 CHAP/CTOC frames readable by mutagen."""
    output_path = _run_cli_with_mocked_io(
        tmp_path,
        monkeypatch,
        [f"Section {i}" for i in range(1, 8)],
        turns_per_section=2,
    )

    chap_frames, ctoc_frames = _read_id3_chapter_frames(output_path)

    assert 3 <= len(chap_frames) <= 5
    assert len(ctoc_frames) == 1
    assert ctoc_frames[0].child_element_ids == [f"chp{i}" for i in range(len(chap_frames))]

    by_id = {frame.element_id: frame for frame in chap_frames}
    previous_end = 0
    for idx in range(len(chap_frames)):
        frame = by_id[f"chp{idx}"]
        assert frame.start_time >= previous_end
        assert frame.end_time > frame.start_time
        previous_end = frame.end_time


def test_signpost_turns_are_rendered_into_output_duration(tmp_path, monkeypatch):
    """Inserted signpost turns are sent through TTS and included in mixed MP3 duration."""
    section_titles = [f"Section {i}" for i in range(1, 8)]
    output_path = _run_cli_with_mocked_io(
        tmp_path,
        monkeypatch,
        section_titles,
        turns_per_section=2,
    )

    chap_frames, _ = _read_id3_chapter_frames(output_path)
    signpost_count = len(chap_frames) - 1

    from mutagen.mp3 import MP3  # pyright: ignore[reportMissingImports]

    audio = MP3(str(output_path))
    non_signpost_turns = len(section_titles) * 2
    non_signpost_seconds = non_signpost_turns * 0.1

    assert signpost_count > 0
    assert audio.info.length > non_signpost_seconds
    assert signpost_count == len(chap_frames) - 1


def test_single_section_pipeline_writes_one_chapter_without_signposts(tmp_path, monkeypatch):
    """A single section remains one chapter, one CTOC child, and zero signpost turns."""
    output_path = _run_cli_with_mocked_io(
        tmp_path,
        monkeypatch,
        ["Only Section"],
        turns_per_section=3,
    )

    chap_frames, ctoc_frames = _read_id3_chapter_frames(output_path)

    assert len(chap_frames) == 1
    assert len(ctoc_frames) == 1
    assert ctoc_frames[0].child_element_ids == ["chp0"]

    script = DialogueScript(
        paper_metadata=_make_paper(["Only Section"], tmp_path / "source.pdf"),
        turns=[
            DialogueTurn(speaker=SpeakerRole.HOST, text="a", section_ref="Only Section"),
            DialogueTurn(speaker=SpeakerRole.EXPERT, text="b", section_ref="Only Section"),
            DialogueTurn(speaker=SpeakerRole.HOST, text="c", section_ref="Only Section"),
        ],
        persona_type=PersonaType.TUTOR,
        language_mode=LanguageMode.EN,
    )
    script, groups = _consolidate_and_insert_signposts(script)
    assert len(groups) == 1
    assert sum(1 for turn in script.turns if turn.is_signpost) == 0


def test_old_dialogue_turn_json_defaults_and_consolidates(tmp_path):
    """Legacy DialogueTurn construction defaults chapter fields and consolidates."""
    turns = [
        DialogueTurn(speaker=SpeakerRole.HOST, text="old intro", section_ref="Intro"),
        DialogueTurn(speaker=SpeakerRole.EXPERT, text="old method", section_ref="Methods"),
    ]

    assert all(turn.chapter_title is None for turn in turns)
    assert all(turn.is_signpost is False for turn in turns)

    groups = consolidate_chapters(turns)
    assert [group.title for group in groups] == ["Intro", "Methods"]


def test_consolidated_chapter_timestamps_are_non_overlapping(tmp_path):
    """_build_chapters returns monotonic, non-overlapping chapter marker windows."""
    section_titles = [f"Section {i}" for i in range(1, 8)]
    turns = []
    for title in section_titles:
        turns.append(DialogueTurn(speaker=SpeakerRole.HOST, text=f"Host {title}", section_ref=title))
        turns.append(DialogueTurn(speaker=SpeakerRole.EXPERT, text=f"Expert {title}", section_ref=title))

    script = DialogueScript(
        paper_metadata=_make_paper(section_titles, tmp_path / "source.pdf"),
        turns=turns,
        persona_type=PersonaType.TUTOR,
        language_mode=LanguageMode.EN,
    )
    script, groups = _consolidate_and_insert_signposts(script)
    segments = [
        AudioSegment(
            speaker=turn.speaker,
            audio_bytes=b"mock",
            duration_seconds=0.1 if turn.is_signpost else 0.2,
            text=turn.text,
        )
        for turn in script.turns
    ]

    chapters, _ = _build_chapters(
        script,
        segments,
        AudioMixer().silence_between_segments_ms,
        chapter_groups=groups,
    )

    for current, nxt in zip(chapters, chapters[1:]):
        assert current.end_time_ms <= nxt.start_time_ms
