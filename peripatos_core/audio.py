"""Audio renderer — synthesizes dialogue turns and assembles final MP3 with chapter markers."""
from __future__ import annotations
import logging
import tempfile
from pathlib import Path
from peripatos_core.exceptions import AudioError
from peripatos_core.providers.tts import TTSProvider
from peripatos_core.types import AudioSegment, ChapterMark, DialogueScript

logger = logging.getLogger(__name__)


class AudioRenderer:
    """Renders a DialogueScript to an MP3 file with ID3v2.4 chapter markers."""

    def __init__(
        self,
        tts: TTSProvider,
        voice_map: dict[str, str] | None = None,
    ) -> None:
        """
        Args:
            tts: TTS provider to use for synthesis.
            voice_map: Optional mapping of speaker name → TTS voice string.
                       e.g. {"Host": "en-US-AriaNeural", "Guest": "en-US-GuyNeural"}
        """
        self._tts = tts
        self._voice_map = voice_map or {}

    def render(self, script: DialogueScript, output_path: Path) -> list[ChapterMark]:
        """Render a dialogue script to an MP3 file.

        Args:
            script: The dialogue script to render.
            output_path: Where to write the final MP3.

        Returns:
            List of ChapterMark objects (one per turn).
        """
        if not script.turns:
            raise AudioError("Cannot render empty dialogue script")

        segments = self._synthesize_turns(script)
        combined_path = self._concatenate_segments(segments)
        chapters = self._compute_chapters(segments)
        self._write_with_chapters(combined_path, output_path, script.title, chapters)
        return chapters

    def _synthesize_turns(self, script: DialogueScript) -> list[AudioSegment]:
        """Synthesize each turn and return AudioSegment list."""
        segments = []
        for i, turn in enumerate(script.turns):
            voice = self._voice_map.get(turn.speaker)
            logger.debug("Synthesizing turn %d/%d: %s", i + 1, len(script.turns), turn.speaker)
            try:
                audio_path = self._tts.synthesize(turn.text, speaker_voice=voice)
            except Exception as exc:
                from peripatos_core.exceptions import TTSError
                raise TTSError(f"TTS failed for turn {i} ({turn.speaker}): {exc}") from exc

            duration_s = self._get_duration(audio_path)
            segments.append(AudioSegment(
                speaker=turn.speaker,
                text=turn.text,
                audio_path=audio_path,
                duration_s=duration_s,
            ))
        return segments

    def _get_duration(self, audio_path: Path) -> float:
        """Get audio duration in seconds using pydub."""
        try:
            from pydub import AudioSegment as PydubSegment  # type: ignore[reportMissingImports]
            seg = PydubSegment.from_file(str(audio_path))
            return len(seg) / 1000.0
        except Exception as exc:
            logger.warning("Could not read duration from %s (using 0.0): %s", audio_path, exc)
            return 0.0

    def _concatenate_segments(self, segments: list[AudioSegment]) -> Path:
        """Concatenate all audio segments into a single MP3 file."""
        try:
            from pydub import AudioSegment as PydubSegment  # type: ignore[reportMissingImports]
        except ImportError as exc:
            raise AudioError("pydub is not installed") from exc

        combined = None
        for seg in segments:
            try:
                audio = PydubSegment.from_file(str(seg.audio_path))
            except Exception as exc:
                logger.warning("Could not decode %s, using silent segment: %s", seg.audio_path, exc)
                audio = PydubSegment.silent(duration=int(seg.duration_s * 1000) or 100)
            combined = audio if combined is None else combined + audio

        if combined is None:
            raise AudioError("No audio segments to concatenate")

        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        combined_path = Path(tmp.name)
        combined.export(str(combined_path), format="mp3")
        return combined_path

    def _compute_chapters(self, segments: list[AudioSegment]) -> list[ChapterMark]:
        """Compute chapter marks from segment durations."""
        chapters = []
        cursor_ms = 0
        for seg in segments:
            duration_ms = int(seg.duration_s * 1000)
            chapters.append(ChapterMark(
                title=seg.speaker,
                start_ms=cursor_ms,
                end_ms=cursor_ms + duration_ms,
            ))
            cursor_ms += duration_ms
        return chapters

    def _write_with_chapters(
        self,
        source_path: Path,
        output_path: Path,
        title: str,
        chapters: list[ChapterMark],
    ) -> None:
        """Copy source MP3 to output and embed ID3v2.4 chapter markers."""
        import shutil
        shutil.copy2(str(source_path), str(output_path))

        try:
            from mutagen.id3 import ID3, ID3NoHeaderError, CHAP, CTOC, TIT2, CTOCFlags  # type: ignore[reportMissingImports]
        except ImportError as exc:
            raise AudioError("mutagen is not installed") from exc

        try:
            tags = ID3(str(output_path))
        except ID3NoHeaderError:
            tags = ID3()

        # Clear existing chapter tags
        tags.delall("CHAP")
        tags.delall("CTOC")

        # Add title
        tags.add(TIT2(encoding=3, text=title))

        # Add CHAP frames
        chap_ids = []
        for i, ch in enumerate(chapters):
            chap_id = f"chp{i}"
            chap_ids.append(chap_id)
            tags.add(CHAP(
                element_id=chap_id,
                start_time=ch.start_ms,
                end_time=ch.end_ms,
                start_offset=0xFFFFFFFF,
                end_offset=0xFFFFFFFF,
                sub_frames=[TIT2(encoding=3, text=ch.title)],
            ))

        # Add CTOC (table of contents)
        tags.add(CTOC(
            element_id="toc",
            flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
            child_element_ids=chap_ids,
            sub_frames=[TIT2(encoding=3, text=title)],
        ))

        tags.save(str(output_path), v2_version=4)
